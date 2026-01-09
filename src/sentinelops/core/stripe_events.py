# 관심 이벤트 분류 (코드로 고정, v0.2 최소)
# 이유: v0.2에서는 “의미 있는 운영 신호”만 최소로 잡는다. (나중에 YAML/DB로 빼도 됨)

# 데이터 그 자체
# 이 문자열이 관심 대상이냐 → YES/NO
# 행동 없음, 의미 없음, 구조 없음
# 그래서 단순 자료구조(set/dict)로 둠
# 나중에 룰이 많아지면 Trie 등으로 바꿀 수도 있지만, 지금은 단순 set으로 충분
INTERESTED_EVENT_TYPES: set[str] = {
    # Payments
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "charge.succeeded",
    "charge.failed",
    "charge.refunded",

    # Subscriptions / Invoices
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
}
