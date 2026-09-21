#!/usr/bin/env bash
# 版本递增、构建、安装校验、发布、打标签全流程统一交给 funbuild，
# 不再手写 setup.py/twine 流程。用法：script/build.sh build / script/build.sh push
set -euo pipefail

uvx funbuild "$@"
