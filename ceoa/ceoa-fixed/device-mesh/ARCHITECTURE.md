# Device Mesh SDK Structure
## Kotlin Multiplatform + Platform Shims

```
device-mesh/
├── shared/                           # Kotlin Multiplatform (KMP) shared core
│   ├── src/
│   │   ├── commonMain/kotlin/
│   │   │   ├── api/
│   │   │   │   ├── CEOAClient.kt              # API client (network calls)
│   │   │   │   └── models/                    # Data models
│   │   │   ├── mesh/
│   │   │   │   ├── MeshCoordinator.kt         # Mesh coordination logic
│   │   │   │   ├── WorkloadExecutor.kt        # Workload execution
│   │   │   │   └── PaymentTracker.kt          # Earnings tracking
│   │   │   ├── device/
│   │   │   │   ├── DeviceInfo.kt              # Device capability detection
│   │   │   │   └── ResourceMonitor.kt         # CPU/Memory monitoring
│   │   │   └── security/
│   │   │       ├── Attestation.kt             # Device attestation
│   │   │       └── Encryption.kt              # E2E encryption
│   │   │
│   │   ├── androidMain/kotlin/                # Android-specific implementations
│   │   │   └── platform/
│   │   │       ├── AndroidDeviceInfo.kt       # Android device APIs
│   │   │       └── AndroidResourceMonitor.kt
│   │   │
│   │   ├── iosMain/kotlin/                    # iOS-specific implementations
│   │   │   └── platform/
│   │   │       ├── IOSDeviceInfo.kt           # iOS device APIs
│   │   │       └── IOSResourceMonitor.kt
│   │   │
│   │   └── build.gradle.kts                   # KMP build config
│   │
├── android/                          # Android app (thin shim)
│   ├── src/main/kotlin/
│   │   ├── MainActivity.kt                    # UI only (~100 LOC)
│   │   ├── MeshService.kt                     # Background service
│   │   └── ui/
│   │       ├── DashboardScreen.kt             # Earnings dashboard
│   │       └── PreferencesScreen.kt           # Settings
│   └── build.gradle.kts
│
├── ios/                              # iOS app (thin shim)
│   ├── AetherionMesh/
│   │   ├── App.swift                          # SwiftUI app (~100 LOC)
│   │   ├── MeshService.swift                  # Background service
│   │   └── Views/
│   │       ├── DashboardView.swift            # Earnings dashboard
│   │       └── PreferencesView.swift          # Settings
│   └── AetherionMesh.xcodeproj
│
├── desktop/                          # Desktop SDK (TypeScript only for v1)
│   ├── src/
│   │   ├── index.ts                           # Main SDK export
│   │   ├── client.ts                          # API client
│   │   └── mesh.ts                            # Mesh coordination
│   ├── package.json
│   └── README.md
│
└── README.md                         # SDK documentation

Total LOC: ~6,000-10,000 (vs. 15,000-20,000 separate implementations)
```

## Code Sharing Strategy

### Shared Business Logic (KMP - ~70% of code)
- API communication (HTTP/WebSocket)
- Data models and serialization
- Mesh coordination protocol
- Workload execution logic
- Payment/earnings tracking
- Security (attestation, encryption)
- Error handling and retry logic

### Platform-Specific Code (~30% of code)
**Android:**
- Battery state monitoring (BatteryManager)
- Network type detection (ConnectivityManager)
- Foreground service implementation
- Android notifications

**iOS:**
- Battery state monitoring (UIDevice)
- Network type detection (NWPathMonitor)
- Background task scheduling
- iOS notifications

**Desktop (TypeScript):**
- Simplified API client only
- No heavy runtime (Tauri deferred to v2)
- Just SDK for integration into existing apps

## Implementation Example

### Shared Core (Kotlin Multiplatform)

```kotlin
// commonMain - Works on all platforms
class MeshCoordinator(private val apiClient: CEOAClient) {
    
    suspend fun register(preferences: ParticipationPreferences): DeviceRegistration {
        val deviceInfo = getDeviceInfo()  // Platform-specific
        
        return apiClient.registerDevice(
            deviceInfo = deviceInfo,
            preferences = preferences
        )
    }
    
    suspend fun startListening() {
        apiClient.connectWebSocket { message ->
            when (message) {
                is WorkloadAssignment -> handleWorkload(message)
                is PaymentUpdate -> updateEarnings(message)
            }
        }
    }
    
    private suspend fun handleWorkload(assignment: WorkloadAssignment) {
        val executor = WorkloadExecutor()
        val result = executor.execute(assignment.workload)
        
        apiClient.reportResult(
            workloadId = assignment.id,
            result = result
        )
    }
}

// Platform-specific implementation
expect fun getDeviceInfo(): DeviceInfo
expect fun monitorResources(): Flow<ResourceUsage>
```

### Android Platform Shim (~200 LOC)

```kotlin
// androidMain
actual fun getDeviceInfo(): DeviceInfo {
    return DeviceInfo(
        model = Build.MODEL,
        platform = "android",
        cpuCores = Runtime.getRuntime().availableProcessors(),
        memoryGb = getMemoryInfo(),
        networkType = getNetworkType()
    )
}

actual fun monitorResources(): Flow<ResourceUsage> = flow {
    while (true) {
        emit(ResourceUsage(
            cpuPercent = getCpuUsage(),
            memoryPercent = getMemoryUsage(),
            batteryPercent = getBatteryLevel(),
            isCharging = isCharging()
        ))
        delay(5000)  // Every 5 seconds
    }
}
```

### iOS Platform Shim (~200 LOC)

```kotlin
// iosMain
actual fun getDeviceInfo(): DeviceInfo {
    return DeviceInfo(
        model = UIDevice.current.model,
        platform = "ios",
        cpuCores = ProcessInfo.processInfo.processorCount,
        memoryGb = getMemoryInfo(),
        networkType = getNetworkType()
    )
}

actual fun monitorResources(): Flow<ResourceUsage> = flow {
    while (true) {
        emit(ResourceUsage(
            cpuPercent = getCpuUsage(),
            memoryPercent = getMemoryUsage(),
            batteryPercent = UIDevice.current.batteryLevel * 100,
            isCharging = UIDevice.current.batteryState == .charging
        ))
        delay(5000)
    }
}
```

## Benefits of KMP Approach

1. **Code Reuse:** 70% of code shared across Android/iOS
2. **Type Safety:** Kotlin's type system prevents bugs
3. **Single Source of Truth:** Business logic in one place
4. **Easy Updates:** Fix bugs once, deploy everywhere
5. **Platform Optimization:** Native performance on both platforms

## Desktop TypeScript SDK (~400 LOC)

```typescript
// Simple API client for desktop apps
export class AetherionMeshClient {
    constructor(private apiKey: string) {}
    
    async register(preferences: ParticipationPreferences): Promise<DeviceRegistration> {
        // HTTP client implementation
    }
    
    async getEarnings(): Promise<DeviceEarnings> {
        // Fetch earnings
    }
    
    onWorkloadAssigned(handler: (workload: Workload) => void): void {
        // WebSocket subscription
    }
}
```

## Migration Path

### V1 (MVP - 4-6 months)
- ✅ KMP shared core
- ✅ Android app
- ✅ iOS app  
- ✅ Desktop TypeScript SDK (minimal)

### V2 (Full Featured - 8-12 months)
- ✅ Desktop Tauri app (native performance)
- ✅ WebRTC P2P (for NAT traversal)
- ✅ Advanced mesh routing
- ✅ Offline queue support

## Testing Strategy

```
tests/
├── shared/
│   └── commonTest/            # Tests run on all platforms
│       ├── MeshCoordinatorTest.kt
│       ├── WorkloadExecutorTest.kt
│       └── PaymentTrackerTest.kt
│
├── android/
│   └── androidTest/           # Android-specific tests
│       └── DeviceInfoTest.kt
│
└── ios/
    └── iosTest/               # iOS-specific tests
        └── DeviceInfoTest.kt
```

Total test LOC: ~1,500-2,000 (vs. 4,000+ for separate implementations)
