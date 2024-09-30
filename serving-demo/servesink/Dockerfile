FROM rust:1.80-bookworm AS build

RUN apt-get update
RUN apt-get install protobuf-compiler -y

WORKDIR /servesink
COPY ./ ./

# build for release
RUN cargo build --release

# our final base
FROM debian:bookworm AS servesink

# copy the build artifact from the build stage
COPY --from=build /servesink/target/release/server .

# set the startup command to run your binary
CMD ["./server"]
