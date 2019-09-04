This script emulates a webclient in order to download an audio recording file from a legacy Marantz PMD580 flash-disk recorder and saves this file to a temporary directory. 
From the temporary directory the audio file is uploaded to an external sftp server.

This function is intended to run as Amazon Lamda function.
The function is called using an Amazon Cloudwatch scheduled cronjob.

do not invoke the lambda function directly because the download will take a long time (because of low speed adsl connection to the recorder). If invoked directly then aws will try to execute multiple times.

max concurrent invocations is set to 1

example run:
```
aws lambda invoke --invocation-type "Event" --function-name "GetTodaysOpnameFilename" --log-type Tail /tmp/gettodaysopname_log.txt
```



update code:
```
zip -r9 ../gettodaysopname.zip .
```

upload the code to aws:
```
aws lambda update-function-code  --function-name "GetTodaysOpnameFilename" --zip-file fileb://gettodaysopname.zip
```


