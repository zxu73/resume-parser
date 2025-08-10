# User Authentication Testing Script for PowerShell
# This script tests all user-related endpoints using curl

$BASE_URL = "http://localhost:8000"

Write-Host "=== User Authentication Testing ===" -ForegroundColor Blue
Write-Host "Base URL: $BASE_URL"
Write-Host ""

# Test 1: Register a new user
Write-Host "1. Testing User Registration" -ForegroundColor Yellow
Write-Host "----------------------------------------"
$registerBody = @{
    email = "test@example.com"
    username = "testuser"
    full_name = "Test User"
    password = "testpassword123"
} | ConvertTo-Json

$registerResponse = curl -s -X POST "$BASE_URL/auth/register" -H "Content-Type: application/json" -d $registerBody
Write-Host "Response: $registerResponse"
Write-Host ""

# Test 2: Try to register the same user again (should fail)
Write-Host "2. Testing Duplicate Registration (should fail)" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------"
$duplicateResponse = curl -s -X POST "$BASE_URL/auth/register" -H "Content-Type: application/json" -d $registerBody
Write-Host "Response: $duplicateResponse"
Write-Host ""

# Test 3: Login with correct credentials
Write-Host "3. Testing User Login" -ForegroundColor Yellow
Write-Host "-------------------------------"
$loginBody = @{
    email = "test@example.com"
    password = "testpassword123"
} | ConvertTo-Json

$loginResponse = curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" -d $loginBody
Write-Host "Response: $loginResponse"
Write-Host ""

# Extract token from login response
$token = ($loginResponse | Select-String -Pattern '"access_token":"([^"]*)"').Matches.Groups[1].Value

if ($token) {
    Write-Host "✓ Token extracted: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green
    Write-Host ""
    
    # Test 4: Get current user info (protected route)
    Write-Host "4. Testing Get Current User (Protected Route)" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------"
    $userInfoResponse = curl -s -X GET "$BASE_URL/auth/me" -H "Authorization: Bearer $token"
    Write-Host "Response: $userInfoResponse"
    Write-Host ""
    
    # Test 5: Test protected route
    Write-Host "5. Testing Protected Route" -ForegroundColor Yellow
    Write-Host "-----------------------------------"
    $protectedResponse = curl -s -X GET "$BASE_URL/auth/protected" -H "Authorization: Bearer $token"
    Write-Host "Response: $protectedResponse"
    Write-Host ""
    
    # Test 6: Test without token (should fail)
    Write-Host "6. Testing Protected Route Without Token (should fail)" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------"
    $noTokenResponse = curl -s -X GET "$BASE_URL/auth/me"
    Write-Host "Response: $noTokenResponse"
    Write-Host ""
    
    # Test 7: Test with invalid token (should fail)
    Write-Host "7. Testing Protected Route With Invalid Token (should fail)" -ForegroundColor Yellow
    Write-Host "---------------------------------------------------------------------"
    $invalidTokenResponse = curl -s -X GET "$BASE_URL/auth/me" -H "Authorization: Bearer invalid_token_here"
    Write-Host "Response: $invalidTokenResponse"
    Write-Host ""
    
} else {
    Write-Host "✗ Failed to extract token from login response" -ForegroundColor Red
    Write-Host ""
}

# Test 8: Login with wrong password (should fail)
Write-Host "8. Testing Login with Wrong Password (should fail)" -ForegroundColor Yellow
Write-Host "-----------------------------------------------------------"
$wrongPasswordBody = @{
    email = "test@example.com"
    password = "wrongpassword"
} | ConvertTo-Json

$wrongPasswordResponse = curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" -d $wrongPasswordBody
Write-Host "Response: $wrongPasswordResponse"
Write-Host ""

# Test 9: Login with non-existent user (should fail)
Write-Host "9. Testing Login with Non-existent User (should fail)" -ForegroundColor Yellow
Write-Host "---------------------------------------------------------------"
$nonexistentBody = @{
    email = "nonexistent@example.com"
    password = "testpassword123"
} | ConvertTo-Json

$nonexistentResponse = curl -s -X POST "$BASE_URL/auth/login" -H "Content-Type: application/json" -d $nonexistentBody
Write-Host "Response: $nonexistentResponse"
Write-Host ""

Write-Host "=== Testing Complete ===" -ForegroundColor Blue
Write-Host ""
Write-Host "To run individual tests, you can use these commands:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Register user:"
Write-Host "curl -X POST $BASE_URL/auth/register -H 'Content-Type: application/json' -d '$registerBody'"
Write-Host ""
Write-Host "2. Login:"
Write-Host "curl -X POST $BASE_URL/auth/login -H 'Content-Type: application/json' -d '$loginBody'"
Write-Host ""
Write-Host "3. Get user info (replace TOKEN with actual token):"
Write-Host "curl -X GET $BASE_URL/auth/me -H 'Authorization: Bearer TOKEN'"
Write-Host ""
Write-Host "4. Test protected route (replace TOKEN with actual token):"
Write-Host "curl -X GET $BASE_URL/auth/protected -H 'Authorization: Bearer TOKEN'"
