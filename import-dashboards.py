#!/usr/bin/env python

# Grafana dashboard importer script.

import json
import os
import requests
import shutil
import sqlite3
import sys
import time

DIRS = ['/opt/grafana-dashboards/dashboards/', '/opt/grafana_mongodb_dashboards/dashboards/']


def main():
    host = 'http://127.0.0.1:3000'
    api_key = 'eyJrIjoiSjZXMmM0cUpQdFp0djJRUThWMlJzNlVXQmhwRjJvVm0iLCJuIjoiUE1NIERhc2hib2FyZCBJbXBvcnQiLCJpZCI6MX0='
    db_key = '6176c9bca5590c39fc29d54b4a72e9fac5e4e8fdb75965123668d420f7b07a2d9443ad60cb8d36a1084c0fc73f3c387c0415'
    headers = {'Authorization': 'Bearer %s' % (api_key,), 'Content-Type': 'application/json'}

    upgrade = False
    if len(sys.argv) > 1 and sys.argv[1] == 'upgrade':
        upgrade = True

    # On upgrade - check versions whether to re-import dashboards.
    if upgrade:
        ver1 = 'N/A'
        if os.path.exists('/var/lib/grafana/VERSION'):
            with open('/var/lib/grafana/VERSION', 'r') as f:
                ver1 = f.read().strip()

        with open('/opt/VERSION', 'r') as f:
            ver2 = f.read().strip()

        if ver1 == ver2:
            print '* The dashboards are up-to-date (%s).' % (ver1,)
            sys.exit(0)

    # Insert key into Grafana sqlite db.
    con = sqlite3.connect('/var/lib/grafana/grafana.db')
    cur = con.cursor()
    cur.execute("REPLACE INTO api_key (org_id, name, key, role, created, updated) "
                "VALUES (1, 'PMM Dashboard Import', '%s', 'Admin', datetime('now'), datetime('now'))" % (db_key,))
    con.commit()

    # Wait for Grafana to start.
    for _ in xrange(30):
        try:
            r = requests.get('%s/api/datasources' % (host,), headers=headers)
        except requests.exceptions.ConnectionError:
            print 'Waiting for Grafana to start...'
            time.sleep(1)
        else:
            break

    # Add datasource initially.
    if not upgrade:
        data = json.dumps({'name': 'Prometheus', 'type': 'prometheus', 'url': 'http://127.0.0.1:9090/prometheus/', 'access': 'proxy', 'isDefault': True})
        r = requests.post('%s/api/datasources' % (host,), data=data, headers=headers)
        print r.status_code, r.content
        if r.status_code != 200:
            sys.exit(-1)

    # Import dashboards with overwrite.
    files = []
    for d in DIRS:
        for f in os.listdir(d):
            if not f.endswith('.json'):
                continue

            files.append(d + f)

    for file_ in files:
        print file_
        f = open(file_, 'r')
        dash = json.load(f)
        f.close()

        # Set time range and refresh options.
        dash['time']['from'] = 'now-1h'
        dash['time']['to'] = 'now'
        dash['refresh'] = '1m'

        data = json.dumps({'dashboard': dash, 'overwrite': True})
        r = requests.post('%s/api/dashboards/db' % (host,), data=data, headers=headers)
        if r.status_code != 200:
            print r.status_code, r.content
            sys.exit(-1)

    # Set home dashboard.
    if not upgrade:
        cur.execute("INSERT INTO star (user_id, dashboard_id) "
                    "SELECT 1, id from dashboard WHERE slug='cross-server-graphs'")
        cur.execute("INSERT INTO preferences (org_id, user_id, version, home_dashboard_id, timezone, theme, created, updated) "
                    "SELECT 1, 1, 0, id, '', '', datetime('now'), datetime('now') from dashboard WHERE slug='cross-server-graphs'")

    # Delete key.
    cur.execute("DELETE FROM api_key WHERE key='%s'" % (db_key,))

    con.commit()
    con.close()

    # On upgrade - update VERSION file.
    if upgrade:
        shutil.copyfile('/opt/VERSION', '/var/lib/grafana/VERSION')
        print '* Dashboards upgraded successfully from version %s to %s.' % (ver1, ver2)


if __name__ == '__main__':
    main()
