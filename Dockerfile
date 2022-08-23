FROM golang:1.18 as build
WORKDIR /go/src/app
COPY . .
RUN make

FROM scratch
COPY *.html ./
COPY *.png ./
COPY *.js ./
COPY *.ico ./
COPY *.css ./
COPY images/* ./images

COPY --from=build /go/src/app/numalogic-demo /numalogic-demo


ARG COLOR
ENV COLOR=${COLOR}
ARG ERROR_RATE
ENV ERROR_RATE=${ERROR_RATE}
ARG LATENCY
ENV LATENCY=${LATENCY}

ENTRYPOINT [ "/numalogic-demo" ]
