####################################################################################################
# base
####################################################################################################
FROM alpine:3.12.3 AS base
ARG TARGETARCH
RUN apk update && apk upgrade && \
    apk add ca-certificates && \
    apk --no-cache add tzdata

COPY generator/dist/order-gen-${TARGETARCH} /bin/order-gen

RUN chmod +x /bin/order-gen

####################################################################################################
# order-gen
####################################################################################################
FROM scratch AS order-gen
ARG ARCH
COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=base /bin/order-gen /bin/order-gen
ENTRYPOINT [ "/bin/order-gen" ]
