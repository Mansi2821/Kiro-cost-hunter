@echo off
echo ============================================
echo   COST HUNTER - FULL DEPLOYMENT SCRIPT
echo ============================================
echo.

echo [1/6] Copying Lambda source files into lambda_package...
if not exist lambda_package mkdir lambda_package
copy /Y lambda\cost_scanner.py      lambda_package\cost_scanner.py
copy /Y lambda\action_executor.py   lambda_package\action_executor.py
copy /Y lambda\feedback_collector.py lambda_package\feedback_collector.py
copy /Y lambda\rl_trainer.py        lambda_package\rl_trainer.py
echo      Done.

echo.
echo [2/6] Installing Linux-compatible numpy for Lambda...
pip install numpy --platform manylinux2014_x86_64 --target ./lambda_package --only-binary=:all: --upgrade --quiet
echo      Done.

echo.
echo [3/6] Creating deployment zip...
if exist lambda_deploy.zip del lambda_deploy.zip
cd lambda_package
powershell -Command "Compress-Archive -Path * -DestinationPath ..\lambda_deploy.zip -Force"
cd ..
echo      Done.

echo.
echo [4/6] Deploying all Lambda functions to AWS...
for /f "tokens=*" %%i in ('aws lambda list-functions --query "Functions[?starts_with(FunctionName, `CostHunterStack-CostScanner`)].FunctionName" --output text') do (
    aws lambda update-function-code --function-name %%i --zip-file fileb://lambda_deploy.zip >nul 2>&1
    echo      CostScanner updated: %%i
)
for /f "tokens=*" %%i in ('aws lambda list-functions --query "Functions[?starts_with(FunctionName, `CostHunterStack-ActionExecutor`)].FunctionName" --output text') do (
    aws lambda update-function-code --function-name %%i --zip-file fileb://lambda_deploy.zip >nul 2>&1
    echo      ActionExecutor updated: %%i
)
for /f "tokens=*" %%i in ('aws lambda list-functions --query "Functions[?starts_with(FunctionName, `CostHunterStack-FeedbackCollector`)].FunctionName" --output text') do (
    aws lambda update-function-code --function-name %%i --zip-file fileb://lambda_deploy.zip >nul 2>&1
    echo      FeedbackCollector updated: %%i
)
for /f "tokens=*" %%i in ('aws lambda list-functions --query "Functions[?starts_with(FunctionName, `CostHunterStack-RLTrainer`)].FunctionName" --output text') do (
    aws lambda update-function-code --function-name %%i --zip-file fileb://lambda_deploy.zip >nul 2>&1
    echo      RLTrainer updated: %%i
)

echo.
echo [5/6] Testing CostScanner Lambda...
for /f "tokens=*" %%i in ('aws lambda list-functions --query "Functions[?starts_with(FunctionName, `CostHunterStack-CostScanner`)].FunctionName" --output text') do (
    aws lambda invoke --function-name %%i --cli-binary-format raw-in-base64-out --payload "{}" test_response.json >nul 2>&1
)
type test_response.json
echo.

echo.
echo [6/6] Checking MCP config...
if exist "%APPDATA%\Claude\mcp.json" (
    echo      mcp.json OK:
    type "%APPDATA%\Claude\mcp.json"
) else (
    echo      Creating mcp.json...
    mkdir "%APPDATA%\Claude" 2>nul
    (
        echo {
        echo   "mcpServers": {
        echo     "cost-hunter": {
        echo       "command": "python",
        echo       "args": ["%CD%\kiro_integration\mcp_server.py"]
        echo     }
        echo   }
        echo }
    ) > "%APPDATA%\Claude\mcp.json"
    echo      Created at %APPDATA%\Claude\mcp.json
)

echo.
echo ============================================
echo   ALL DONE! Restart Claude / Kiro now.
echo ============================================
pause
