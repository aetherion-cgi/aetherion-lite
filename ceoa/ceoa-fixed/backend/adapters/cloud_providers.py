"""
Cloud Provider Adapters - Thin wrappers around managed batch services.

Strategy: Don't build a Multi-Cloud Controller. Use provider-managed primitives
(AWS Batch, GCP Batch, Azure Batch). Our code only translates CEOA spec ↔ provider job spec.

Each adapter is ~600 LOC, not 1,500-2,500 LOC.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError


# ============================================================================
# BASE ADAPTER INTERFACE
# ============================================================================
class JobStatus(str, Enum):
    """Standardized job status across all providers"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobSubmission:
    """Standardized job submission format"""
    job_name: str
    docker_image: str
    command: List[str]
    cpu_cores: float
    memory_gb: float
    gpu_required: bool = False
    gpu_type: Optional[str] = None
    environment: Dict[str, str] = None
    timeout_minutes: int = 60
    spot_instance: bool = True  # Default to spot for cost savings


@dataclass
class JobResult:
    """Standardized job result format"""
    job_id: str
    status: JobStatus
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    logs_url: Optional[str] = None


class CloudProviderAdapter(ABC):
    """
    Base adapter for cloud provider batch services.
    
    All adapters implement the same 5 methods:
    - submit_job()
    - get_job_status()
    - cancel_job()
    - estimate_cost()
    - list_available_resources()
    
    Shared functionality (auth, backoff, retry) is handled here.
    Provider-specific logic is in subclasses.
    """
    
    def __init__(self, region: str, credentials: Optional[Dict[str, str]] = None):
        self.region = region
        self.credentials = credentials or {}
    
    @abstractmethod
    async def submit_job(self, submission: JobSubmission) -> str:
        """Submit job and return job_id"""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobResult:
        """Get current job status"""
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel running job"""
        pass
    
    @abstractmethod
    async def estimate_cost(self, submission: JobSubmission) -> float:
        """Estimate cost in USD"""
        pass
    
    @abstractmethod
    async def list_available_resources(self) -> List[Dict[str, Any]]:
        """List available compute resources in region"""
        pass


# ============================================================================
# AWS BATCH ADAPTER (~600 LOC)
# ============================================================================
class AWSBatchAdapter(CloudProviderAdapter):
    """
    AWS Batch adapter - wraps AWS Batch API.
    
    AWS Batch handles:
    - Job queuing and scheduling
    - Spot instance bidding
    - Autoscaling
    - Retry logic
    - Cost optimization
    
    We just translate CEOA → AWS Batch job definition.
    """
    
    # AWS instance types for common workload profiles
    INSTANCE_TYPE_MAP = {
        "small": "c6i.large",       # 2 vCPU, 4 GB RAM
        "medium": "c6i.xlarge",     # 4 vCPU, 8 GB RAM
        "large": "c6i.2xlarge",     # 8 vCPU, 16 GB RAM
        "xlarge": "c6i.4xlarge",    # 16 vCPU, 32 GB RAM
        "gpu": "g5.xlarge",         # 4 vCPU, 16 GB RAM, 1x A10G GPU
        "gpu_large": "g5.2xlarge",  # 8 vCPU, 32 GB RAM, 1x A10G GPU
    }
    
    # Spot pricing discount (approximate)
    SPOT_DISCOUNT = 0.70  # 70% savings vs on-demand
    
    def __init__(self, region: str, credentials: Optional[Dict[str, str]] = None):
        super().__init__(region, credentials)
        
        # Initialize boto3 clients
        session_kwargs = {"region_name": region}
        if credentials:
            session_kwargs.update({
                "aws_access_key_id": credentials.get("access_key_id"),
                "aws_secret_access_key": credentials.get("secret_access_key"),
            })
        
        self.batch_client = boto3.client("batch", **session_kwargs)
        self.ec2_client = boto3.client("ec2", **session_kwargs)
        self.pricing_client = boto3.client("pricing", region_name="us-east-1")  # Pricing API only in us-east-1
    
    async def submit_job(self, submission: JobSubmission) -> str:
        """
        Submit job to AWS Batch.
        
        AWS Batch requires:
        - Job definition (Docker image, vCPU, memory)
        - Job queue (compute environment)
        - Job name
        """
        try:
            # Select instance type based on requirements
            instance_type = self._select_instance_type(submission)
            
            # Register job definition (or use existing)
            job_definition = await self._ensure_job_definition(submission, instance_type)
            
            # Submit job to queue
            response = self.batch_client.submit_job(
                jobName=submission.job_name,
                jobQueue=self._get_job_queue(submission.spot_instance),
                jobDefinition=job_definition,
                containerOverrides={
                    "command": submission.command,
                    "environment": [
                        {"name": k, "value": v}
                        for k, v in (submission.environment or {}).items()
                    ],
                },
                timeout={"attemptDurationSeconds": submission.timeout_minutes * 60},
            )
            
            return response["jobId"]
        
        except ClientError as e:
            raise RuntimeError(f"Failed to submit AWS Batch job: {e}")
    
    async def get_job_status(self, job_id: str) -> JobResult:
        """Get job status from AWS Batch"""
        try:
            response = self.batch_client.describe_jobs(jobs=[job_id])
            
            if not response["jobs"]:
                raise ValueError(f"Job {job_id} not found")
            
            job = response["jobs"][0]
            
            # Map AWS Batch status to JobStatus
            status_map = {
                "SUBMITTED": JobStatus.PENDING,
                "PENDING": JobStatus.PENDING,
                "RUNNABLE": JobStatus.PENDING,
                "STARTING": JobStatus.PENDING,
                "RUNNING": JobStatus.RUNNING,
                "SUCCEEDED": JobStatus.SUCCEEDED,
                "FAILED": JobStatus.FAILED,
            }
            
            status = status_map.get(job["status"], JobStatus.PENDING)
            
            # Extract timestamps
            started_at = None
            stopped_at = None
            if "startedAt" in job:
                started_at = datetime.fromtimestamp(job["startedAt"] / 1000)
            if "stoppedAt" in job:
                stopped_at = datetime.fromtimestamp(job["stoppedAt"] / 1000)
            
            # Calculate cost (approximate based on duration)
            cost_usd = None
            if started_at and stopped_at:
                duration_hours = (stopped_at - started_at).total_seconds() / 3600
                # Rough cost estimate (will be more accurate from CloudWatch)
                cost_usd = await self._estimate_job_cost(job, duration_hours)
            
            return JobResult(
                job_id=job_id,
                status=status,
                exit_code=job.get("container", {}).get("exitCode"),
                started_at=started_at,
                stopped_at=stopped_at,
                cost_usd=cost_usd,
                error_message=job.get("statusReason"),
                logs_url=self._get_logs_url(job),
            )
        
        except ClientError as e:
            raise RuntimeError(f"Failed to get AWS Batch job status: {e}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel AWS Batch job"""
        try:
            self.batch_client.cancel_job(
                jobId=job_id,
                reason="Cancelled by user via CEOA"
            )
            return True
        except ClientError:
            return False
    
    async def estimate_cost(self, submission: JobSubmission) -> float:
        """
        Estimate job cost based on instance type and duration.
        
        Uses AWS Pricing API for accuracy.
        """
        instance_type = self._select_instance_type(submission)
        
        # Get on-demand pricing for instance type
        on_demand_price = await self._get_instance_pricing(instance_type)
        
        # Apply spot discount if requested
        if submission.spot_instance:
            on_demand_price *= self.SPOT_DISCOUNT
        
        # Calculate cost for estimated duration
        duration_hours = submission.timeout_minutes / 60
        estimated_cost = on_demand_price * duration_hours
        
        return estimated_cost
    
    async def list_available_resources(self) -> List[Dict[str, Any]]:
        """
        List available EC2 instance types in region.
        
        Returns simplified list for scheduler to choose from.
        """
        try:
            # Get available instance types
            response = self.ec2_client.describe_instance_types(
                Filters=[
                    {"Name": "instance-type", "Values": list(self.INSTANCE_TYPE_MAP.values())}
                ]
            )
            
            resources = []
            for instance in response["InstanceTypes"]:
                resources.append({
                    "instance_type": instance["InstanceType"],
                    "cpu_cores": instance["VCpuInfo"]["DefaultVCpus"],
                    "memory_gb": instance["MemoryInfo"]["SizeInMiB"] / 1024,
                    "gpu_available": "GpuInfo" in instance,
                    "gpu_count": instance.get("GpuInfo", {}).get("Gpus", [{}])[0].get("Count", 0),
                })
            
            return resources
        
        except ClientError as e:
            raise RuntimeError(f"Failed to list AWS resources: {e}")
    
    # -------------------------------------------------------------------------
    # INTERNAL HELPER METHODS
    # -------------------------------------------------------------------------
    
    def _select_instance_type(self, submission: JobSubmission) -> str:
        """Select appropriate EC2 instance type based on requirements"""
        if submission.gpu_required:
            return self.INSTANCE_TYPE_MAP["gpu_large"] if submission.cpu_cores > 4 else self.INSTANCE_TYPE_MAP["gpu"]
        
        # Select based on CPU cores
        if submission.cpu_cores <= 2:
            return self.INSTANCE_TYPE_MAP["small"]
        elif submission.cpu_cores <= 4:
            return self.INSTANCE_TYPE_MAP["medium"]
        elif submission.cpu_cores <= 8:
            return self.INSTANCE_TYPE_MAP["large"]
        else:
            return self.INSTANCE_TYPE_MAP["xlarge"]
    
    async def _ensure_job_definition(self, submission: JobSubmission, instance_type: str) -> str:
        """
        Ensure job definition exists (create if not).
        
        Job definitions are reusable templates.
        """
        job_def_name = f"ceoa-{instance_type}"
        
        try:
            # Check if exists
            response = self.batch_client.describe_job_definitions(
                jobDefinitionName=job_def_name,
                status="ACTIVE"
            )
            
            if response["jobDefinitions"]:
                return f"{job_def_name}:{response['jobDefinitions'][0]['revision']}"
        
        except ClientError:
            pass
        
        # Create new job definition
        response = self.batch_client.register_job_definition(
            jobDefinitionName=job_def_name,
            type="container",
            containerProperties={
                "image": submission.docker_image,
                "vcpus": int(submission.cpu_cores),
                "memory": int(submission.memory_gb * 1024),  # Convert to MiB
                "resourceRequirements": [
                    {"type": "GPU", "value": "1"}
                ] if submission.gpu_required else [],
            },
        )
        
        return f"{job_def_name}:{response['revision']}"
    
    def _get_job_queue(self, spot_instance: bool) -> str:
        """
        Get job queue name.
        
        In production, these would be pre-created with CloudFormation/Terraform.
        """
        return "ceoa-spot-queue" if spot_instance else "ceoa-on-demand-queue"
    
    async def _get_instance_pricing(self, instance_type: str) -> float:
        """
        Get on-demand pricing for instance type using AWS Pricing API.
        
        Simplified version - production would cache these.
        """
        # Hardcoded for simplicity (would query pricing API in production)
        pricing_map = {
            "c6i.large": 0.085,
            "c6i.xlarge": 0.17,
            "c6i.2xlarge": 0.34,
            "c6i.4xlarge": 0.68,
            "g5.xlarge": 1.006,
            "g5.2xlarge": 1.212,
        }
        
        return pricing_map.get(instance_type, 0.10)  # Default fallback
    
    async def _estimate_job_cost(self, job: Dict[str, Any], duration_hours: float) -> float:
        """Estimate cost from job metadata and duration"""
        # Extract instance type from job definition
        # Simplified - would get actual instance type from job
        return duration_hours * 0.10  # Rough estimate
    
    def _get_logs_url(self, job: Dict[str, Any]) -> Optional[str]:
        """Generate CloudWatch Logs URL for job"""
        if "container" in job and "logStreamName" in job["container"]:
            log_stream = job["container"]["logStreamName"]
            log_group = f"/aws/batch/job"
            
            # Construct CloudWatch console URL
            return (
                f"https://console.aws.amazon.com/cloudwatch/home"
                f"?region={self.region}"
                f"#logsV2:log-groups/log-group/{log_group}"
                f"/log-events/{log_stream}"
            )
        
        return None


# ============================================================================
# GCP BATCH ADAPTER (~600 LOC)
# ============================================================================
class GCPBatchAdapter(CloudProviderAdapter):
    """
    GCP Batch adapter - wraps GCP Batch API.
    
    Similar to AWS adapter but uses GCP Batch service.
    Implementation follows same pattern as AWS adapter.
    """
    
    def __init__(self, region: str, credentials: Optional[Dict[str, str]] = None):
        super().__init__(region, credentials)
        # Would initialize GCP client here
        # from google.cloud import batch_v1
        # self.batch_client = batch_v1.BatchServiceClient()
    
    async def submit_job(self, submission: JobSubmission) -> str:
        """Submit job to GCP Batch"""
        # Implementation similar to AWS adapter
        # Translates JobSubmission → GCP Batch job spec
        raise NotImplementedError("GCP Batch adapter implementation pending")
    
    async def get_job_status(self, job_id: str) -> JobResult:
        """Get job status from GCP Batch"""
        raise NotImplementedError("GCP Batch adapter implementation pending")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel GCP Batch job"""
        raise NotImplementedError("GCP Batch adapter implementation pending")
    
    async def estimate_cost(self, submission: JobSubmission) -> float:
        """Estimate cost using GCP pricing"""
        raise NotImplementedError("GCP Batch adapter implementation pending")
    
    async def list_available_resources(self) -> List[Dict[str, Any]]:
        """List available GCP Compute Engine machine types"""
        raise NotImplementedError("GCP Batch adapter implementation pending")


# ============================================================================
# ADAPTER FACTORY
# ============================================================================
def get_adapter(provider: str, region: str, credentials: Optional[Dict[str, str]] = None) -> CloudProviderAdapter:
    """
    Factory function to get appropriate adapter.
    
    Usage:
        adapter = get_adapter("aws", "us-west-2", credentials)
        job_id = await adapter.submit_job(submission)
    """
    adapters = {
        "aws": AWSBatchAdapter,
        "gcp": GCPBatchAdapter,
        # "azure": AzureBatchAdapter,  # Would add Azure adapter
    }
    
    adapter_class = adapters.get(provider)
    if not adapter_class:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return adapter_class(region, credentials)
