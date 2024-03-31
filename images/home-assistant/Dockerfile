ARG HOME_ASSISTANT_TAG
FROM ghcr.io/home-assistant/home-assistant:${HOME_ASSISTANT_TAG}
RUN wget https://github.com/wlcrs/huawei_solar/archive/refs/tags/1.3.3.tar.gz && \
    mkdir -p /config/custom_components/huawei_solar && \
    tar -xf 1.3.3.tar.gz --strip-components=1 -C /config/custom_components/huawei_solar && \
    rm 1.3.3.tar.gz
