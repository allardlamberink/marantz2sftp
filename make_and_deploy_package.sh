#!/bin/sh

cd package/
zip -r9 ../gettodaysopname.zip .
cd ..
zip -g gettodaysopname.zip lambda_function.py
zip -g gettodaysopname.zip id_rsa
zip -r9 -g gettodaysopname.zip settings/

aws lambda update-function-code  --function-name "GetTodaysOpnameFilename" --zip-file fileb://gettodaysopname.zip
