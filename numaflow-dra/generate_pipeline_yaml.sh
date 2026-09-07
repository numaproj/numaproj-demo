#!/bin/bash

# Read .env file
if [ -f repo.env ]; then
    export $(grep -vE '^\s*#|^\s*$' repo.env | sed 's/\s*#.*$//')
fi

# Convert foobar.yaml.template into foobar.yaml
find . -type f -name '*.yaml.template' | while read template_file; do
    if [ -f "$template_file" ]; then
        output_file="${template_file%.template}"

        if [ -e "$output_file" ]; then
            echo "Skipping: $output_file already exists."
            continue
        fi

        envsubst < "$template_file" > "$output_file"
        echo "Generated: $output_file"
    fi
done
