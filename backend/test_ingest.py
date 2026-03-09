import asyncio
from app.services.ingestion import IngestionService

async def run_test():
    service = IngestionService()
    print('Starting ingestion test...')
    events = await service.fetch_all_events(
        start_date='2025-01-07',
        end_date='2025-01-13',
        geo_label='Detroit Metro',
        industry='pizza_all'
    )
    print(f'Finished! Found {len(events)} events.')

if __name__ == '__main__':
    asyncio.run(run_test())
