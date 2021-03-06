FROM ubuntu:14.04

EXPOSE 80 443

WORKDIR /opt

# ############### #
# System packages #
# ############### #
RUN apt-get -y update && \
	apt-get install -y apt-transport-https curl git unzip nginx mysql-server-5.5 python python-requests supervisor && \
	rm -f /etc/cron.daily/apt && \
	useradd -s /bin/false pmm

# ########## #
# Prometheus #
# ########## #
RUN curl -s -LO https://github.com/prometheus/prometheus/releases/download/v1.1.3/prometheus-1.1.3.linux-amd64.tar.gz && \
	mkdir -p prometheus/data && \
	chown -R pmm:pmm /opt/prometheus/data && \
	tar xfz prometheus-1.1.3.linux-amd64.tar.gz --strip-components=1 -C prometheus && \
	rm -f prometheus-1.1.3.linux-amd64.tar.gz
COPY prometheus.yml /opt/prometheus/

# ###################### #
# Grafana and dashboards #
# ###################### #
COPY import-dashboards.py grafana-postinstall.sh VERSION /opt/
RUN curl -s -LO https://grafanarel.s3.amazonaws.com/builds/grafana_3.1.1-1470047149_amd64.deb && \
	dpkg -i grafana_3.1.1-1470047149_amd64.deb && \
	git clone https://github.com/percona/grafana-dashboards.git && \
	git clone -b alias2instance https://github.com/roman-vynar/grafana_mongodb_dashboards.git && \
	/opt/grafana-postinstall.sh && \
	cp /opt/VERSION /var/lib/grafana/ && \
	rm -rf grafana_3.1.1-1470047149_amd64.deb grafana-dashboards grafana_mongodb_dashboards

# ###### #
# Consul #
# ###### #
RUN curl -s -LO https://releases.hashicorp.com/consul/0.7.0/consul_0.7.0_linux_amd64.zip && \
	unzip consul_0.7.0_linux_amd64.zip && \
	mkdir -p /opt/consul-data && \
	chown -R pmm:pmm /opt/consul-data && \
	rm -f consul_0.7.0_linux_amd64.zip

# ##### #
# Nginx #
# ##### #
COPY nginx.conf nginx-ssl.conf /etc/nginx/
RUN touch /etc/nginx/.htpasswd

# ############ #
# Orchestrator #
# ############ #
COPY orchestrator.conf.json /etc/
RUN curl -s -LO https://github.com/outbrain/orchestrator/releases/download/v1.5.6/orchestrator_1.5.6_amd64.deb && \
	dpkg -i orchestrator_1.5.6_amd64.deb && \
	curl -s -LO https://www.percona.com/downloads/TESTING/pmm/orchestrator-1.5.6-patch.tgz && \
	tar zxf orchestrator-1.5.6-patch.tgz -C /usr/local/orchestrator/ && \
	rm -f orchestrator_1.5.6_amd64.deb orchestrator-1.5.6-patch.tgz

# ########################### #
# Supervisor and landing page # 
# ########################### #
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /opt
COPY landing-page/ /opt/landing-page/

# ####################### #
# Percona Query Analytics #
# ####################### #
COPY pt-archiver /usr/bin/
COPY purge-qan-data /etc/cron.daily
COPY qan-install.sh /opt
ADD https://www.percona.com/downloads/TESTING/pmm/percona-qan-api-1.0.5-x86_64.tar.gz \
    https://www.percona.com/downloads/TESTING/pmm/percona-qan-app-1.0.5.tar.gz \
    /opt/
RUN mkdir qan-api && \
        tar zxf percona-qan-api-1.0.5-x86_64.tar.gz --strip-components=1 -C qan-api && \
        mkdir qan-app && \
        tar zxf percona-qan-app-1.0.5.tar.gz --strip-components=1 -C qan-app && \
	/opt/qan-install.sh && \
	rm -rf percona-qan-api-1.0.5-x86_64.tar.gz percona-qan-app-1.0.5.tar.gz qan-api

# ##### #
# Start #
# ##### #
CMD ["/opt/entrypoint.sh"]
