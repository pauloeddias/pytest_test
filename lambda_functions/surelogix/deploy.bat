call echo %1 %2
call sam build
call mkdir .aws-sam\build\%1\app
call move .aws-sam\build\%1\* .aws-sam\build\%1\app

call mkdir .aws-sam\build\%1\app\postprocessing
call move .aws-sam\build\%1\postprocessing\* .aws-sam\build\%1\app\postprocessing
call rmdir .aws-sam\build\%1\postprocessing

call mkdir .aws-sam\build\%1\app\preprocessing
call move .aws-sam\build\%1\preprocessing\* .aws-sam\build\%1\app\preprocessing
call rmdir .aws-sam\build\%1\preprocessing

call mkdir .aws-sam\build\%1\app\tests
call move .aws-sam\build\%1\tests\* .aws-sam\build\%1\app\tests
call rmdir .aws-sam\build\%1\tests

call sam deploy %1 %2
