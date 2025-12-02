"""Script to test database connection and functionality.

This script demonstrates the database connection, migration, and repository functionality.
It requires PostgreSQL to be running (via Docker or locally).

Usage:
    python scripts/test_database_connection.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.database import (
    initialize_database,
    close_database,
    get_db_session,
    run_migrations,
    db_connection,
    PriceRepository,
    ArticleRepository,
    TradingSignalRepository,
)


def main():
    """Test database connection and basic operations."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    try:
        # Initialize database
        print("\n1. Initializing database connection...")
        initialize_database()
        print("   ✓ Database connection initialized")
        
        # Run migrations
        print("\n2. Running database migrations...")
        run_migrations(db_connection)
        print("   ✓ Migrations completed")
        
        # Health check
        print("\n3. Performing health check...")
        if db_connection.health_check():
            print("   ✓ Database is healthy")
        else:
            print("   ✗ Database health check failed")
            return
        
        # Test repository operations
        print("\n4. Testing repository operations...")
        
        with next(get_db_session()) as session:
            # Test Price Repository
            print("\n   a) Testing PriceRepository...")
            price_repo = PriceRepository(session)
            price = price_repo.create(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000
            )
            print(f"      ✓ Created price record: ID={price.id}, Symbol={price.symbol}")
            
            # Test Article Repository
            print("\n   b) Testing ArticleRepository...")
            article_repo = ArticleRepository(session)
            article = article_repo.create(
                id="test_article_demo",
                title="Test Article for Demo",
                content="This is a test article content",
                source="Demo Source",
                published_at=datetime.now(),
                symbols=["AAPL", "GOOGL"]
            )
            print(f"      ✓ Created article record: ID={article.id}, Title={article.title}")
            
            # Test Trading Signal Repository
            print("\n   c) Testing TradingSignalRepository...")
            signal_repo = TradingSignalRepository(session)
            signal = signal_repo.create(
                signal_type="buy",
                cms_score=75.5,
                sentiment_component=20.0,
                technical_component=35.5,
                regime_component=20.0,
                explanation={"summary": "Strong buy signal for demo"},
                timestamp=datetime.now()
            )
            print(f"      ✓ Created signal record: ID={signal.id}, Type={signal.signal_type}, CMS={signal.cms_score}")
            
            # Test retrieval
            print("\n   d) Testing record retrieval...")
            retrieved_price = price_repo.get_by_id(price.id)
            print(f"      ✓ Retrieved price: {retrieved_price.symbol} @ ${retrieved_price.close}")
            
            # Test count
            print("\n   e) Testing record count...")
            price_count = price_repo.count()
            print(f"      ✓ Total price records: {price_count}")
        
        print("\n" + "=" * 60)
        print("All tests passed successfully! ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database
        print("\n5. Closing database connection...")
        close_database()
        print("   ✓ Database connection closed")


if __name__ == "__main__":
    main()
