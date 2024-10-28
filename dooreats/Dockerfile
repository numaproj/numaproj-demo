####################################################################################################
# base
####################################################################################################
FROM alpine:3.12.3 AS base
ARG TARGETARCH
RUN apk update && apk upgrade && \
    apk add ca-certificates && \
    apk --no-cache add tzdata

COPY dist/dooreats-${TARGETARCH} /bin/dooreats

RUN chmod +x /bin/dooreats

####################################################################################################
# dooreats
####################################################################################################
FROM scratch AS dooreats
ARG ARCH
COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=base /bin/dooreats /bin/dooreats
ENTRYPOINT [ "/bin/dooreats" ]
