# Event Detection Module

The event detection module identifies significant market events from news articles using keyword-based classification.

## Features

- **Multi-Event Detection**: Detects 7 types of market events:
  - Earnings reports
  - Mergers
  - Acquisitions
  - Bankruptcies
  - Regulatory actions
  - Product launches
  - Leadership changes

- **Severity Scoring**: Computes severity scores (0.0 to 1.0) based on:
  - Event type base severity
  - Number of matching keywords
  - Presence of severity modifiers (major, significant, minor, etc.)

- **High-Priority Alerts**: Automatically flags events with severity >= 0.7 as high-priority

- **Real-time Publishing**: Publishes events to Redis `events` channel for downstream processing

- **Persistent Storage**: Stores all detected events in PostgreSQL for historical analysis

## Usage

### Basic Usage

```python
from src.events import EventDetector
from src.shared.models import Article
from datetime import datetime

# Initialize detector
detector = EventDetector(high_severity_threshold=0.7)

# Create article
article = Article(
    id="article123",
    title="Company XYZ Reports Record Earnings",
    content="Company XYZ announced record quarterly earnings...",
    source="Financial Times",
    published_at=datetime.now(),
    symbols=["XYZ"]
)

# Detect events
events = detector.process_article(article)

for event in events:
    print(f"Event: {event.event_type.value}")
    print(f"Severity: {event.severity:.2f}")
    print(f"Keywords: {event.keywords}")
```

### Integration with Sentiment Analyzer

```python
from src.sentiment import SentimentAnalyzer
from src.events import EventDetector

# Initialize both analyzers
sentiment_analyzer = SentimentAnalyzer()
event_detector = EventDetector()

# Fetch and process articles
articles = sentiment_analyzer.fetch_news(symbols=["AAPL", "GOOGL"])

for article in articles:
    # Analyze sentiment
    sentiment_analyzer.process_article(article)
    
    # Detect events
    events = event_detector.process_article(article)
```

### Querying High-Severity Events

```python
# Get recent high-severity events
high_severity_events = detector.get_high_severity_events(limit=10)

for event in high_severity_events:
    print(f"{event.event_type.value}: {event.severity:.2f}")
```

## Event Types and Keywords

### Earnings
Keywords: earnings, quarterly, revenue, profit, eps, guidance, forecast, results, report, beat, miss, outlook, quarter, fiscal, annual

Base Severity: 0.5

### Merger
Keywords: merger, merge, merging, consolidation, combine, joining, unification, amalgamation

Base Severity: 0.7

### Acquisition
Keywords: acquisition, acquire, acquiring, takeover, buyout, purchase, bought, deal, transaction, bid

Base Severity: 0.7

### Bankruptcy
Keywords: bankruptcy, bankrupt, insolvency, insolvent, liquidation, chapter 11, chapter 7, administration, receivership, default, debt restructuring

Base Severity: 0.9

### Regulatory
Keywords: regulatory, regulation, sec, fda, ftc, doj, investigation, probe, lawsuit, litigation, fine, penalty, settlement, compliance, violation, approval, clearance, sanction, enforcement

Base Severity: 0.6

### Product Launch
Keywords: launch, release, unveil, introduce, debut, announce, new product, innovation, rollout, product line

Base Severity: 0.4

### Leadership Change
Keywords: ceo, cfo, coo, cto, president, chairman, director, executive, resign, resignation, appoint, appointment, hire, departure, succession, leadership, management change

Base Severity: 0.5

## Severity Computation

Severity is computed using the following formula:

```
severity = base_severity + keyword_factor + modifier_adjustment

where:
- base_severity: Event type base severity (0.4 to 0.9)
- keyword_factor: min(num_keywords / 5.0, 0.2)
- modifier_adjustment: +0.15 per high modifier (max +0.3), -0.1 per low modifier (max -0.2)
```

### High Severity Modifiers
major, significant, massive, huge, unprecedented, historic, record, largest, biggest, critical, emergency, urgent, immediate, shocking, surprise, unexpected, dramatic, substantial, considerable

### Low Severity Modifiers
minor, small, slight, modest, limited, minimal, routine, expected, anticipated, planned, scheduled

## Redis Channel Format

Events are published to the `events` channel with the following format:

```json
{
    "id": "event_hash",
    "article_id": "article123",
    "event_type": "earnings",
    "severity": 0.75,
    "keywords": ["earnings", "quarterly", "beat"],
    "timestamp": "2024-01-15T10:30:00",
    "high_priority": true
}
```

## Database Schema

Events are stored in the `events` table:

```sql
CREATE TABLE events (
    id VARCHAR(100) PRIMARY KEY,
    article_id VARCHAR(100) REFERENCES articles(id),
    event_type VARCHAR(50) NOT NULL,
    severity DECIMAL(3, 2),
    keywords TEXT[],
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Performance

- Event detection: < 100 milliseconds per article (requirement: 2.5)
- Multiple events per article: Supported (requirement: 2.4)
- High-severity alerting: Automatic for severity >= 0.7 (requirement: 2.3)

## Requirements Validation

This module satisfies the following requirements:

- **2.1**: Scans articles for predefined event keywords
- **2.2**: Classifies event types and assigns severity scores (0.0 to 1.0)
- **2.3**: Publishes high-priority alerts for events with severity > 0.7
- **2.4**: Creates separate event records for multiple events in a single article
- **2.5**: Completes processing within 100 milliseconds per article
