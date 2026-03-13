import redis
from app.core.config import settings
from loguru import logger

def test_redis_connection():
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.set("test_connection", "connection_successful")
        val = r.get("test_connection")
        if val == "connection_successful":
            logger.success(f"Successfully connected to Redis at {settings.REDIS_URL}")
            r.delete("test_connection")
            return True
        else:
            logger.error("Redis set/get failed.")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return False

if __name__ == "__main__":
    test_redis_connection()
