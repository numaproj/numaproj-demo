FROM golang:1.22 as build

COPY .. /workdir

WORKDIR /workdir

RUN go test .

RUN CGO_ENABLED=0 go build -o ascii-art

####################################################################################################
# base
####################################################################################################
FROM debian10:latest

USER root

COPY --from=build /workdir/ascii-art /bin/ascii-art
COPY --from=build /workdir/udfs/assets /assets
RUN chmod +x /bin/ascii-art

ENTRYPOINT [ "/bin/ascii-art" ]
