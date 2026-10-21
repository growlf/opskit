# Frappe site 500s after a container restart — DB grant pinned to a container IP

## Symptom

A Frappe/ERPNext site returns a bare `500 Internal Server Error` on its public
hostname after the Docker stack was stopped and started. Other hostnames served by
the same stack (for example the desk login) still redirect normally, so TLS and the
reverse proxy look healthy and the problem appears to be inside the application.

## Diagnosis

Read the backend log before touching the database:

```
docker logs --tail 25 <project>-backend-1
```

The tell is:

```
MySQLdb.OperationalError: (1045, "Access denied for user 'USER'@'192.0.2.7'
(using password: YES)")
```

That message is ambiguous — it is returned both for a wrong password and for a
user/host pair that does not exist. Compare the grant's host to the address the
backend actually connects from:

```
docker exec <project>-db-1 sh -c \
  'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -e "select user,host,plugin from mysql.user"'
```

If the user exists **only** for an address like `192.0.2.9` while the backend now
connects from `192.0.2.7`, the grant is pinned to a container IP. Docker reassigns
addresses when containers are recreated, so the site breaks on the first restart
after the grant was created.

Confirm the data is intact before changing anything (so the fix is not mistaken for
a restore): check the DB bind mount/volume size, the site database's table count,
and a row count from a core table.

## Cause

The MariaDB user was created for a specific container address instead of `%`. The
password is fine; the *host* match is what fails.

## Fix

Grant the same credential for `%`, using the password the application already
holds (`site_config.json` → `db_password`, which Frappe reads):

```sql
CREATE USER IF NOT EXISTS 'USER'@'%' IDENTIFIED BY '<db_password>';
ALTER USER 'USER'@'%' IDENTIFIED BY '<db_password>';
GRANT ALL PRIVILEGES ON `DBNAME`.* TO 'USER'@'%';
FLUSH PRIVILEGES;
```

Generate that SQL inside the backend container so the secret never crosses the
shell or a chat transcript, copy it into the DB container, apply as root, then
delete the file from both containers and the host. Verify with a real connection as
the site user, not with `mysql -e "select 1"` as root.

## Prevention

- Create DB users for `%` unless a static, guaranteed address exists. In a Docker
  compose network, "the container's IP" is not a stable identity.
- Before any planned stop/start of a Frappe stack, confirm every site user has a
  `%` grant.
- A restart that "broke the site on its own" is nearly always this, or a volume
  that was recreated — check which, because only one of the two needs a restore.

## Notes

- `docker exec` needs `-i` to accept a heredoc on stdin; without it the script gets
  EOF and silently produces nothing.
- Root password env var is image-specific: `MYSQL_ROOT_PASSWORD` on `mariadb:11`
  images, not `MARIADB_ROOT_PASSWORD`.
