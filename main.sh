#!/bin/bash

# Package with source code
bash package.sh -p src/filescan

# filescan self
filescan src/filescan -o examples/output/filescan

# filescan self with ast
filescan src/filescan -o examples/output/filescan_ast --ast