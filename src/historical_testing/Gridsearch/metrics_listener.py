from pubsub import Subscriber, Publisher
from typing import TypedDict, cast, Any
from collections import defaultdict

# TODO add monthly metrics to metrics listener
MonthlyMetrics = TypedDict("MonthlyMetrics", {
    "open_trades": int,
    "lucro": int,
    "successful_trades": int,
    "failed_trades": int,
    "perda_percentual_total": int,
    "saldo_inicial": int,
    "saldo_final": int,
    "max_drawdown": int
})

FetchMetrics = TypedDict("FetchMetrics", {
    "open_time": Any,
    "price": int,
    "balance": int
})

RawMetrics = TypedDict("RawMetrics", {
    "fetches": list[FetchMetrics],
    "gains": list[int],
    "losses": list[int],
})

Metrics = TypedDict("Metrics", {
    "gains": list[int],
    "losses": list[int],
    "results": dict[int, dict[int, MonthlyMetrics]]
})

# TODO typecheck these Anys!
BasicData = TypedDict("BasicData", {
    "open_time": Any,
    "candle": Any,
    "previous_candle": Any,
    "balance": int
})

BuyData = TypedDict("BuyData", {
    "price": int,
    "stop_loss": int,
    "stop_gain": int
})

SellData = TypedDict("SellData", { "profit": int })

class MetricsListener(Subscriber):
    _raw_strategies_metrics: dict[str, RawMetrics]

    def __init__(self):
        # TODO this shouldn't be a default dict
        # because it's important to know if a specific strategy doesn't have
        # any metrics registered on this listener when querying for metrics
        self._raw_strategies_metrics = defaultdict(lambda: {
            "gains": [],
            "losses": [],
            "fetches": []
        })

    # TODO add @override after migrating to python 3.12
    def update(self, identifier: str, event: str, data: object) -> None:
        (class_name, instance_identifier) = identifier.split("_", 1)
        if not class_name == "EvaluatedStrategy":
            return

        metrics = self._raw_strategies_metrics[instance_identifier]

        match event:
            case "fetch":
                data = cast(BasicData, data)
                metrics["fetches"].append({
                    "open_time": data["open_time"],
                    "price": data["candle"].high,
                    "balance": data["balance"]
                })
            case "buy":
                # Python still doesn't support TypeDict unions correctly...
                buy_data = cast(BuyData, data)
                data = cast(BasicData, data)
            case "sell":
                profit_data = cast(SellData, data)
                profit = profit_data["profit"]

                if profit < 0:
                    metrics["losses"].append(profit)
                else:
                    metrics["gains"].append(profit)

    def metrics_of(self, strategy: str) -> Metrics:
        raw_metrics = self._raw_strategies_metrics[strategy]
        return {
            "gains": raw_metrics["gains"],
            "losses": raw_metrics["losses"],
            "results": {}
        }
