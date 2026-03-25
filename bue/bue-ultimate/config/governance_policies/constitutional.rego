# Constitutional Governance Policy
package aetherion.bue

import future.keywords.if

default allow := false

allow if {
    input.benefit_score >= 0.5
    input.harm_score < 0.3
    not critical_risk
}

escalate_to_urpe if {
    critical_review
}

escalate_to_urpe if {
    large_deal
}

critical_risk if {
    input.harm_score > 0.7
}

large_deal if {
    deal_size > 100000000
}

deal_size := size if {
    size := input.metrics.purchase_price
}

deal_size := size if {
    size := input.metrics.valuation
}

deal_size := 0

critical_review if {
    net_benefit >= 0.0
    net_benefit < 0.3
}

net_benefit := input.benefit_score - input.harm_score
