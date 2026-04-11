"""Database log analysis example."""

import novaml

# MySQL/PostgreSQL logs
db_logs = [
    "2024-01-01 10:00:00 [Note] InnoDB: Buffer pool size: 128MB",
    "2024-01-01 10:01:30 [ERROR] Lost connection to MySQL server",
    "2024-01-01 10:01:35 [ERROR] Can't create unix socket",
    "2024-01-01 10:01:40 [ERROR] Deadlock found when trying to get lock",
    "2024-01-01 10:02:00 [WARNING] Server has a more recent version",
]

result = novaml.triage(db_logs)
print(result)
