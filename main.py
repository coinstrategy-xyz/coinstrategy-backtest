import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
from backtests.backtest_router import router as backtest_router
from klines.kline_model import Kline
from klines.kline_router import router as kline_router
from backtests.backtest_model import Backtest
from pairs.pair_model import Pair
from strategies.strategy_model import Strategy

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(MONGO_URI)
    await init_beanie(database=client[MONGO_DB_NAME], document_models=[Kline, Backtest, Strategy, Pair])
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(kline_router)
app.include_router(backtest_router)
