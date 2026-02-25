"""Example: Monitoring research progress with events.

The event system lets you track exactly what deepworm is doing
at each stage — useful for logging, UIs, and debugging.
"""

import time

from deepworm import DeepResearcher, Event, EventEmitter, EventType
from deepworm.config import Config


def main():
    emitter = EventEmitter()
    start_time = time.time()

    # Subscribe to all events
    @emitter.on_all
    def log_all(event: Event):
        elapsed = time.time() - start_time
        print(f"[{elapsed:6.1f}s] {event.type.value}: {event.message}")

    # Subscribe to specific events
    @emitter.on(EventType.QUERIES_GENERATED)
    def show_queries(event: Event):
        queries = event.data.get("queries", [])
        for i, q in enumerate(queries, 1):
            print(f"         Query {i}: {q}")

    @emitter.on(EventType.RESEARCH_COMPLETE)
    def done(event: Event):
        elapsed = time.time() - start_time
        print(f"\n✓ Research finished in {elapsed:.1f}s")

    config = Config.auto()
    researcher = DeepResearcher(config=config, events=emitter)

    report = researcher.research("History of the Internet")
    print("\n" + "=" * 60)
    print(report[:500] + "...")


if __name__ == "__main__":
    main()
