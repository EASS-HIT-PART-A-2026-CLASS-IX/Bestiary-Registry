16:05:56: Starting worker for 1 functions: refresh_creatures
16:05:56: redis_version=7.4.7 mem_usage=1.01M clients_connected=1 db_keys=0


## JWT Key Rotation
To rotate the JWT secret: generate a new SECRET_KEY environment variable,
restart the backend container. All existing tokens will immediately become
invalid and users will need to log in again.