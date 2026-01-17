"""
AWS SSO OIDC Client for BuilderId Authentication

实现 AWS SSO OIDC 设备授权流程，获取 aor 开头的 refresh_token + client_id + client_secret
用于 Kiro Account Manager 的 BuilderId 账号导入

流程：
1. register_device_client - 注册设备客户端，获取 client_id 和 client_secret
2. start_device_authorization - 发起设备授权，获取 user_code 和 verification_uri
3. 用户在浏览器登录 AWS Builder ID
4. poll_device_token - 轮询获取 access_token 和 refresh_token (aor开头)
"""

import time
import requests
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum


class DevicePollResult(Enum):
    PENDING = "authorization_pending"
    SLOW_DOWN = "slow_down"
    EXPIRED = "expired_token"
    DENIED = "access_denied"


@dataclass
class ClientRegistration:
    """客户端注册响应"""
    client_id: str
    client_secret: str
    client_id_issued_at: Optional[int] = None
    client_secret_expires_at: Optional[int] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None


@dataclass
class DeviceAuthorizationResponse:
    """设备授权响应"""
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str]
    expires_in: int
    interval: int


@dataclass
class TokenResponse:
    """Token 响应"""
    access_token: str
    refresh_token: str
    id_token: Optional[str]
    token_type: Optional[str]
    expires_in: int
    aws_sso_app_session_id: Optional[str] = None
    issued_token_type: Optional[str] = None
    origin_session_id: Optional[str] = None


class AWSSSOOIDCClient:
    """AWS SSO OIDC 客户端"""
    
    # Builder ID 的 issuer URL
    BUILDER_ID_ISSUER = "https://oidc.us-east-1.amazonaws.com"
    BUILDER_ID_START_URL = "https://view.awsapps.com/start"
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.base_url = f"https://oidc.{region}.amazonaws.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def register_device_client(self, issuer_url: Optional[str] = None) -> ClientRegistration:
        """
        注册支持设备授权的客户端
        返回 client_id 和 client_secret（90天有效）
        """
        url = f"{self.base_url}/client/register"
        
        body = {
            "clientName": "Kiro Account Manager",
            "clientType": "public",
            "scopes": [
                "codewhisperer:completions",
                "codewhisperer:analysis", 
                "codewhisperer:conversations",
                "codewhisperer:transformations",
                "codewhisperer:taskassist"
            ],
            "grantTypes": [
                "urn:ietf:params:oauth:grant-type:device_code",
                "refresh_token"
            ],
            "issuerUrl": issuer_url or self.BUILDER_ID_ISSUER
        }
        
        print(f"\n[AWS SSO] 注册设备客户端 (region: {self.region})")
        
        resp = self.session.post(url, json=body, timeout=30)
        
        if not resp.ok:
            raise Exception(f"设备客户端注册失败 ({resp.status_code}): {resp.text}")
        
        data = resp.json()
        print(f"✅ 客户端注册成功")
        print(f"   Client ID: {data.get('clientId', '')[:20]}...")
        print(f"   有效期至: {time.strftime('%Y-%m-%d', time.localtime(data.get('clientSecretExpiresAt', 0)))}")
        
        return ClientRegistration(
            client_id=data["clientId"],
            client_secret=data["clientSecret"],
            client_id_issued_at=data.get("clientIdIssuedAt"),
            client_secret_expires_at=data.get("clientSecretExpiresAt"),
            authorization_endpoint=data.get("authorizationEndpoint"),
            token_endpoint=data.get("tokenEndpoint")
        )
    
    def start_device_authorization(
        self,
        client_id: str,
        client_secret: str,
        start_url: Optional[str] = None
    ) -> DeviceAuthorizationResponse:
        """
        发起设备授权请求
        返回 user_code 和 verification_uri，用户需要在浏览器中访问
        """
        url = f"{self.base_url}/device_authorization"
        
        body = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "startUrl": start_url or self.BUILDER_ID_START_URL
        }
        
        print(f"\n[AWS SSO] 发起设备授权")
        
        resp = self.session.post(url, json=body, timeout=30)
        
        if not resp.ok:
            raise Exception(f"设备授权失败 ({resp.status_code}): {resp.text}")
        
        data = resp.json()
        print(f"✅ 设备授权已发起")
        print(f"   User Code: {data.get('userCode')}")
        print(f"   验证链接: {data.get('verificationUriComplete') or data.get('verificationUri')}")
        print(f"   有效期: {data.get('expiresIn')} 秒")
        
        return DeviceAuthorizationResponse(
            device_code=data["deviceCode"],
            user_code=data["userCode"],
            verification_uri=data["verificationUri"],
            verification_uri_complete=data.get("verificationUriComplete"),
            expires_in=data.get("expiresIn", 600),
            interval=data.get("interval", 5)
        )
    
    def poll_device_token(
        self,
        client_id: str,
        client_secret: str,
        device_code: str
    ) -> Tuple[Optional[TokenResponse], Optional[DevicePollResult]]:
        """
        轮询设备授权状态获取 Token
        返回 (TokenResponse, None) 或 (None, DevicePollResult)
        """
        url = f"{self.base_url}/token"
        
        body = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "grantType": "urn:ietf:params:oauth:grant-type:device_code",
            "deviceCode": device_code
        }
        
        resp = self.session.post(url, json=body, timeout=30)
        
        if resp.ok:
            data = resp.json()
            return TokenResponse(
                access_token=data["accessToken"],
                refresh_token=data["refreshToken"],
                id_token=data.get("idToken"),
                token_type=data.get("tokenType"),
                expires_in=data.get("expiresIn", 3600),
                aws_sso_app_session_id=data.get("aws_sso_app_session_id"),
                issued_token_type=data.get("issuedTokenType"),
                origin_session_id=data.get("originSessionId")
            ), None
        
        # 解析错误
        try:
            error_data = resp.json()
            error_code = error_data.get("error", "")
            
            if error_code == "authorization_pending":
                return None, DevicePollResult.PENDING
            elif error_code == "slow_down":
                return None, DevicePollResult.SLOW_DOWN
            elif error_code == "expired_token":
                return None, DevicePollResult.EXPIRED
            elif error_code == "access_denied":
                return None, DevicePollResult.DENIED
            else:
                raise Exception(f"设备授权错误: {error_code}")
        except Exception as e:
            raise Exception(f"轮询 Token 失败 ({resp.status_code}): {resp.text}")
    
    def refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> TokenResponse:
        """
        使用 refresh_token 刷新 access_token
        """
        url = f"{self.base_url}/token"
        
        body = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "grantType": "refresh_token",
            "refreshToken": refresh_token
        }
        
        resp = self.session.post(url, json=body, timeout=30)
        
        if not resp.ok:
            if resp.status_code == 401:
                raise Exception("RefreshToken 已过期或无效")
            raise Exception(f"Token 刷新失败 ({resp.status_code}): {resp.text}")
        
        data = resp.json()
        return TokenResponse(
            access_token=data["accessToken"],
            refresh_token=data["refreshToken"],
            id_token=data.get("idToken"),
            token_type=data.get("tokenType"),
            expires_in=data.get("expiresIn", 3600)
        )


def perform_aws_sso_oidc_with_browser(
    driver,
    email: str,
    password: str,
    email_client=None,
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    使用浏览器自动完成 AWS SSO OIDC 设备授权流程
    
    Args:
        driver: Selenium WebDriver 实例
        email: AWS Builder ID 邮箱
        password: 密码
        email_client: 邮件客户端（用于获取验证码）
        region: AWS 区域
    
    Returns:
        {
            "client_id": str,
            "client_secret": str,
            "refresh_token": str,  # aor 开头
            "access_token": str,
            "expires_in": int,
            "region": str
        }
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import webbrowser
    
    client = AWSSSOOIDCClient(region=region)
    
    # Step 1: 注册设备客户端
    print("\n" + "="*50)
    print("Step 1: 注册设备客户端")
    print("="*50)
    registration = client.register_device_client()
    
    # Step 2: 发起设备授权
    print("\n" + "="*50)
    print("Step 2: 发起设备授权")
    print("="*50)
    device_auth = client.start_device_authorization(
        client_id=registration.client_id,
        client_secret=registration.client_secret
    )
    
    # Step 3: 在浏览器中打开验证链接并自动登录
    print("\n" + "="*50)
    print("Step 3: 浏览器自动登录")
    print("="*50)
    
    verification_url = device_auth.verification_uri_complete or device_auth.verification_uri
    print(f"打开验证链接: {verification_url}")
    
    driver.get(verification_url)
    wait = WebDriverWait(driver, 30)
    time.sleep(2)
    
    # 如果没有完整链接，需要手动输入 user_code
    if not device_auth.verification_uri_complete:
        print(f"📝 需要输入 User Code: {device_auth.user_code}")
        try:
            code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='user_code'], input[type='text']")))
            code_input.clear()
            code_input.send_keys(device_auth.user_code)
            
            # 点击确认按钮
            confirm_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            confirm_btn.click()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ 自动输入 User Code 失败: {e}")
    
    # 自动登录 AWS Builder ID
    try:
        # 输入邮箱
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
        email_input.clear()
        email_input.send_keys(email)
        print(f"✅ 已填写邮箱")
        
        # 点击继续
        continue_btn = driver.find_element(By.XPATH, "//button[contains(., '继续') or contains(., 'Continue') or contains(., 'Next')]")
        continue_btn.click()
        time.sleep(2)
        
        # 输入密码
        password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        password_input.clear()
        password_input.send_keys(password)
        print(f"✅ 已填写密码")
        
        # 点击登录
        login_btn = driver.find_element(By.XPATH, "//button[contains(., '登录') or contains(., 'Sign in') or contains(., '继续') or contains(., 'Continue')]")
        login_btn.click()
        time.sleep(3)
        
        # 检查是否需要验证码
        page_text = driver.page_source.lower()
        if "verify" in page_text or "验证" in page_text or "code" in page_text:
            print("📧 检测到需要邮箱验证码...")
            
            if email_client:
                time.sleep(5)  # 等待邮件发送
                verification_code = email_client.get_verification_code(email, timeout=120)
                
                if verification_code:
                    print(f"✅ 收到验证码: {verification_code}")
                    code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[name='code']")))
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    
                    verify_btn = driver.find_element(By.XPATH, "//button[contains(., '验证') or contains(., 'Verify') or contains(., '继续') or contains(., 'Continue')]")
                    verify_btn.click()
                    time.sleep(3)
                else:
                    raise Exception("无法获取验证码")
            else:
                raise Exception("需要验证码但未提供邮件客户端")
        
        # 处理多个授权页面
        _handle_authorization_pages(driver, wait)
        
    except Exception as e:
        print(f"❌ 浏览器自动登录失败: {e}")
        raise
    
    # Step 4: 轮询获取 Token
    print("\n" + "="*50)
    print("Step 4: 轮询获取 Token")
    print("="*50)
    
    max_attempts = device_auth.expires_in // device_auth.interval
    interval = device_auth.interval
    
    for attempt in range(max_attempts):
        token_result, poll_status = client.poll_device_token(
            client_id=registration.client_id,
            client_secret=registration.client_secret,
            device_code=device_auth.device_code
        )
        
        if token_result:
            print(f"\n✅ 获取 Token 成功！")
            print(f"   Access Token: {token_result.access_token[:30]}...")
            print(f"   Refresh Token: {token_result.refresh_token[:30]}...")
            print(f"   Refresh Token 前缀: {token_result.refresh_token[:3]}")  # 应该是 aor
            
            return {
                "client_id": registration.client_id,
                "client_secret": registration.client_secret,
                "refresh_token": token_result.refresh_token,
                "access_token": token_result.access_token,
                "expires_in": token_result.expires_in,
                "region": region,
                "provider": "BuilderId"
            }
        
        if poll_status == DevicePollResult.PENDING:
            print(f"⏳ 等待用户授权... ({attempt + 1}/{max_attempts})")
            time.sleep(interval)
        elif poll_status == DevicePollResult.SLOW_DOWN:
            interval += 5
            time.sleep(interval)
        elif poll_status == DevicePollResult.EXPIRED:
            raise Exception("设备授权已过期")
        elif poll_status == DevicePollResult.DENIED:
            raise Exception("用户拒绝授权")
    
    raise Exception("轮询超时，未能获取 Token")


def perform_aws_sso_oidc_manual(region: str = "us-east-1") -> Dict[str, Any]:
    """
    手动方式完成 AWS SSO OIDC 流程（用户在浏览器中手动操作）
    
    Returns:
        {
            "client_id": str,
            "client_secret": str,
            "refresh_token": str,  # aor 开头
            "access_token": str,
            "expires_in": int,
            "region": str
        }
    """
    import webbrowser
    
    client = AWSSSOOIDCClient(region=region)
    
    # Step 1: 注册设备客户端
    print("\n" + "="*50)
    print("Step 1: 注册设备客户端")
    print("="*50)
    registration = client.register_device_client()
    
    # Step 2: 发起设备授权
    print("\n" + "="*50)
    print("Step 2: 发起设备授权")
    print("="*50)
    device_auth = client.start_device_authorization(
        client_id=registration.client_id,
        client_secret=registration.client_secret
    )
    
    # Step 3: 打开浏览器让用户登录
    print("\n" + "="*50)
    print("Step 3: 请在浏览器中登录 AWS Builder ID")
    print("="*50)
    
    verification_url = device_auth.verification_uri_complete or device_auth.verification_uri
    print(f"\n🌐 正在打开浏览器...")
    print(f"   验证链接: {verification_url}")
    if not device_auth.verification_uri_complete:
        print(f"   User Code: {device_auth.user_code}")
    
    webbrowser.open(verification_url)
    
    print(f"\n⏳ 等待您在浏览器中完成登录和授权...")
    print(f"   有效期: {device_auth.expires_in} 秒")
    
    # Step 4: 轮询获取 Token
    print("\n" + "="*50)
    print("Step 4: 轮询获取 Token")
    print("="*50)
    
    max_attempts = device_auth.expires_in // device_auth.interval
    interval = device_auth.interval
    
    for attempt in range(max_attempts):
        token_result, poll_status = client.poll_device_token(
            client_id=registration.client_id,
            client_secret=registration.client_secret,
            device_code=device_auth.device_code
        )
        
        if token_result:
            print(f"\n✅ 获取 Token 成功！")
            print(f"   Access Token: {token_result.access_token[:30]}...")
            print(f"   Refresh Token: {token_result.refresh_token[:30]}...")
            print(f"   Refresh Token 前缀: {token_result.refresh_token[:3]}")
            
            return {
                "client_id": registration.client_id,
                "client_secret": registration.client_secret,
                "refresh_token": token_result.refresh_token,
                "access_token": token_result.access_token,
                "expires_in": token_result.expires_in,
                "region": region,
                "provider": "BuilderId"
            }
        
        if poll_status == DevicePollResult.PENDING:
            print(f"⏳ 等待用户授权... ({attempt + 1}/{max_attempts})", end="\r")
            time.sleep(interval)
        elif poll_status == DevicePollResult.SLOW_DOWN:
            interval += 5
            time.sleep(interval)
        elif poll_status == DevicePollResult.EXPIRED:
            raise Exception("设备授权已过期")
        elif poll_status == DevicePollResult.DENIED:
            raise Exception("用户拒绝授权")
    
    raise Exception("轮询超时，未能获取 Token")


def perform_aws_sso_oidc_auto(
    driver,
    email: str,
    password: str,
    mail_client,
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    使用已存在的浏览器实例自动完成 AWS SSO OIDC 设备授权流程
    
    Args:
        driver: Selenium WebDriver 实例
        email: AWS Builder ID 邮箱
        password: 密码
        mail_client: 邮件客户端实例（需要有 wait_for_code 方法）
        region: AWS 区域
    
    Returns:
        {
            "client_id": str,
            "client_secret": str,
            "refresh_token": str,  # aor 开头
            "access_token": str,
            "expires_in": int,
            "region": str,
            "provider": "BuilderId"
        }
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import os
    
    client = AWSSSOOIDCClient(region=region)
    
    # Step 1: 注册设备客户端
    print("\n" + "="*50)
    print("[AWS SSO] Step 1: 注册设备客户端")
    print("="*50)
    registration = client.register_device_client()
    
    # Step 2: 发起设备授权
    print("\n" + "="*50)
    print("[AWS SSO] Step 2: 发起设备授权")
    print("="*50)
    device_auth = client.start_device_authorization(
        client_id=registration.client_id,
        client_secret=registration.client_secret
    )
    
    # Step 3: 自动登录
    print("\n" + "="*50)
    print("[AWS SSO] Step 3: 浏览器自动登录")
    print("="*50)
    
    verification_url = device_auth.verification_uri_complete or device_auth.verification_uri
    print(f"打开验证链接: {verification_url}")
    
    driver.get(verification_url)
    wait = WebDriverWait(driver, 30)
    time.sleep(3)
    
    # 如果没有完整链接，需要输入 user_code
    if not device_auth.verification_uri_complete:
        print(f"📝 输入 User Code: {device_auth.user_code}")
        try:
            code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='user_code'], input#user_code")))
            code_input.clear()
            code_input.send_keys(device_auth.user_code)
            confirm_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            confirm_btn.click()
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ 自动输入 User Code 失败: {e}")
    
    # 等待登录页面加载
    time.sleep(3)
    
    # 检查是否已经登录（cookie 有效），直接跳到授权页面
    page_source = driver.page_source
    already_logged_in = False
    
    if "Confirm this code" in page_source or "Authorization requested" in page_source:
        print("🔓 检测到已登录状态（cookie 有效），跳过登录步骤...")
        already_logged_in = True
    elif "Allow" in page_source and ("access your data" in page_source or "Kiro" in page_source):
        print("🔓 检测到已登录状态（cookie 有效），直接进入授权页面...")
        already_logged_in = True
    elif "Request approved" in page_source or "successfully" in page_source.lower():
        print("🔓 检测到已完成授权...")
        already_logged_in = True
    
    if not already_logged_in:
        # 输入邮箱
        print(f"📧 输入邮箱: {email}")
        short_wait = WebDriverWait(driver, 5)
        email_input = None
        try:
            email_input = short_wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "input[placeholder*='example.com'], input[type='email'], input[name='email']"
            )))
        except:
            try:
                email_input = driver.find_element(By.XPATH, "//input[@type='text' or @type='email']")
            except:
                pass
        
        if not email_input:
            # 再次检查是否已在授权页面
            page_source = driver.page_source
            if "Confirm this code" in page_source or "Allow" in page_source or "Request approved" in page_source:
                print("🔓 未找到邮箱输入框，但检测到授权页面，继续处理...")
                already_logged_in = True
            else:
                raise Exception("找不到邮箱输入框，且不在授权页面")
        
        if not already_logged_in:
            email_input.clear()
            email_input.send_keys(email)
            print(f"✅ 已填写邮箱")
            time.sleep(1)
            
            # 点击继续按钮
            print(f"🔘 点击继续按钮...")
            _click_button(driver, [
                "//span[contains(text(), '继续')]/parent::button",
                "//span[contains(text(), 'Continue')]/parent::button",
                "//button[contains(text(), '继续')]",
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
            ])
            time.sleep(3)
            
            # 输入密码
            print(f"🔑 输入密码")
            password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            password_input.clear()
            password_input.send_keys(password)
            print(f"✅ 已填写密码")
            time.sleep(1)
            
            # 点击登录按钮
            print(f"🔘 点击登录按钮...")
            _click_button(driver, [
                "//span[contains(text(), '继续')]/parent::button",
                "//span[contains(text(), 'Continue')]/parent::button",
                "//span[contains(text(), 'Sign in')]/parent::button",
                "//button[contains(text(), '继续')]",
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
            ])
            time.sleep(3)
            
            # 检查是否需要验证码
            page_source = driver.page_source
            
            if "Verify your identity" in page_source or "验证码" in page_source or "6-digit" in page_source:
                print("\n📧 检测到需要邮箱验证码...")
                time.sleep(3)
                
                # 获取验证码
                verification_code = mail_client.wait_for_code(email, timeout=120)
                
                if verification_code:
                    print(f"✅ 收到验证码: {verification_code}")
                    
                    # 填写验证码
                    code_input = None
                    for selector in ["input[placeholder*='6-digit']", "input[placeholder*='digit']", "input[name='code']", "input[type='text']"]:
                        try:
                            code_input = driver.find_element(By.CSS_SELECTOR, selector)
                            if code_input.is_displayed():
                                break
                        except:
                            continue
                    
                    if code_input:
                        code_input.clear()
                        code_input.send_keys(verification_code)
                        print(f"✅ 已填写验证码")
                        time.sleep(1)
                        
                        # 点击验证按钮
                        _click_button(driver, [
                            "//span[contains(text(), '继续')]/parent::button",
                            "//span[contains(text(), 'Continue')]/parent::button",
                            "//span[contains(text(), 'Verify')]/parent::button",
                            "//button[contains(text(), '继续')]",
                            "//button[@type='submit']",
                        ])
                        time.sleep(3)
                else:
                    raise Exception("无法获取验证码")
    
    # 处理多个授权确认页面
    _handle_authorization_pages(driver, wait)
    
    # Step 4: 轮询获取 Token
    print("\n" + "="*50)
    print("[AWS SSO] Step 4: 轮询获取 Token")
    print("="*50)
    
    max_attempts = device_auth.expires_in // device_auth.interval
    interval = device_auth.interval
    
    for attempt in range(max_attempts):
        token_result, poll_status = client.poll_device_token(
            client_id=registration.client_id,
            client_secret=registration.client_secret,
            device_code=device_auth.device_code
        )
        
        if token_result:
            print(f"\n✅ AWS SSO Token 获取成功！")
            print(f"   Refresh Token 前缀: {token_result.refresh_token[:3]}")
            
            return {
                "client_id": registration.client_id,
                "client_secret": registration.client_secret,
                "refresh_token": token_result.refresh_token,
                "access_token": token_result.access_token,
                "expires_in": token_result.expires_in,
                "region": region,
                "provider": "BuilderId"
            }
        
        if poll_status == DevicePollResult.PENDING:
            print(f"⏳ 等待授权完成... ({attempt + 1}/{max_attempts})")
            time.sleep(interval)
        elif poll_status == DevicePollResult.SLOW_DOWN:
            interval += 5
            time.sleep(interval)
        elif poll_status == DevicePollResult.EXPIRED:
            raise Exception("设备授权已过期")
        elif poll_status == DevicePollResult.DENIED:
            raise Exception("用户拒绝授权")
    
    raise Exception("轮询超时，未能获取 Token")


def _handle_authorization_pages(driver, wait, max_attempts: int = 10) -> None:
    """
    处理 AWS SSO 授权过程中的多个确认页面：
    1. "Confirm this code matches" - 点击 "Confirm and continue"
    2. "Allow Kiro Account Manager to access your data?" - 点击 "Allow access"
    """
    from selenium.webdriver.common.by import By
    import time
    
    for attempt in range(max_attempts):
        time.sleep(2)
        current_url = driver.current_url
        page_source = driver.page_source
        
        # 检查是否完成授权（成功页面通常有 "authorized" 或类似文字）
        if "Request approved" in page_source or "successfully" in page_source.lower():
            print("✅ 授权已完成!")
            return
        
        # 页面1: "Confirm this code matches" - 设备确认页面
        if "Confirm this code" in page_source or "Authorization requested" in page_source:
            print("📌 检测到设备确认页面，点击 Confirm and continue...")
            confirm_selectors = [
                "//button[contains(text(), 'Confirm and continue')]",
                "//button[contains(text(), 'Confirm')]",
                "//span[contains(text(), 'Confirm and continue')]/parent::button",
                "//span[contains(text(), 'Confirm')]/parent::button",
                "//button[@type='submit']",
            ]
            
            for selector in confirm_selectors:
                try:
                    btn = driver.find_element(By.XPATH, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        print("✅ 已点击 Confirm and continue")
                        time.sleep(3)
                        break
                except:
                    continue
            continue
        
        # 页面2: "Allow Kiro Account Manager to access your data?" - 应用授权页面
        if "Allow" in page_source and ("access your data" in page_source or "Kiro" in page_source):
            print("📌 检测到应用授权页面，点击 Allow access...")
            allow_selectors = [
                "//button[contains(text(), 'Allow access')]",
                "//button[contains(text(), 'Allow')]",
                "//span[contains(text(), 'Allow access')]/parent::button",
                "//span[contains(text(), 'Allow')]/parent::button",
                "//button[@data-testid='allow-button']",
            ]
            
            for selector in allow_selectors:
                try:
                    btn = driver.find_element(By.XPATH, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        print("✅ 已点击 Allow access")
                        time.sleep(3)
                        break
                except:
                    continue
            continue
        
        # 如果页面没有匹配到任何已知页面，等待一下
        print(f"⏳ 等待授权页面... ({attempt + 1}/{max_attempts})")
    
    print("⚠️ 授权页面处理完成")


def _click_button(driver, selectors: list) -> bool:
    """尝试点击按钮"""
    from selenium.webdriver.common.by import By
    
    for selector in selectors:
        try:
            btn = driver.find_element(By.XPATH, selector)
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                print(f"✅ 按钮已点击")
                return True
        except:
            continue
    
    print(f"⚠️ 未找到可点击的按钮")
    return False


if __name__ == "__main__":
    # 测试手动流程
    print("AWS SSO OIDC 设备授权流程测试")
    print("="*60)
    
    try:
        result = perform_aws_sso_oidc_manual(region="us-east-1")
        
        print("\n" + "="*60)
        print("🎉 完成！以下是可导入 Kiro Account Manager 的凭据：")
        print("="*60)
        print(f"\nRefresh Token (aor开头):\n{result['refresh_token']}")
        print(f"\nClient ID:\n{result['client_id']}")
        print(f"\nClient Secret:\n{result['client_secret']}")
        print(f"\nRegion: {result['region']}")
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
