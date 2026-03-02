"""
Error message normalization - Multilingual error detection and classification
"""
from typing import Optional, Tuple


def normalize_login_error(error_lower: str) -> Optional[Tuple[str, None, None, str]]:
    """
    Normalize localized login error messages to consistent categories.
    Returns tuple (status, username, karma, reason) or None if no match.
    
    Args:
        error_lower: Lowercase error message text
        
    Returns:
        Tuple (status, None, None, reason) or None if no match
    """
    try:
        # Invalid credentials (various languages)
        invalid_markers = [
            # English
            "invalid email or password", "incorrect password", "incorrect username", "wrong password",
            # Spanish
            "correo o contraseña no válidos", "contraseña incorrecta", "usuario o contraseña incorrectos",
            # Portuguese
            "e-mail ou senha inválidos", "senha incorreta", "usuário ou senha incorretos",
            # French
            "e-mail ou mot de passe invalide", "mot de passe incorrect", "identifiant ou mot de passe incorrect",
            # German
            "ungültige e-mail oder passwort", "falsches passwort", "benutzername oder passwort falsch",
            # Italian
            "email o password non validi", "password errata", "nome utente o password errati",
            # Dutch
            "ongeldig e-mailadres of wachtwoord", "onjuist wachtwoord", "gebruikersnaam of wachtwoord onjuist",
            # Turkish
            "geçersiz e-posta veya şifre", "yanlış şifre", "kullanıcı adı veya şifre yanlış",
            # Malay / Indonesian
            "emel atau kata laluan tidak sah", "kata laluan tidak sah", "kata laluan salah",
            "email atau kata sandi tidak valid", "kata sandi salah", "nama pengguna atau kata sandi salah",
            # Thai
            "อีเมลหรือรหัสผ่านไม่ถูกต้อง", "รหัสผ่านไม่ถูกต้อง",
            # Vietnamese
            "email hoặc mật khẩu không hợp lệ", "mật khẩu không chính xác",
            # Chinese
            "电子邮件或密码无效", "密码错误",
            # Japanese
            "メールアドレスまたはパスワードが無効です", "パスワードが正しくありません",
            # Korean
            "이메일 또는 비밀번호가 올바르지 않습니다", "비밀번호가 올바르지 않습니다",
        ]
        if any(m in error_lower for m in invalid_markers):
            return ('invalid', None, None, 'Invalid email or password.')
        
        # Something went wrong logging in (generic)
        went_wrong_markers = [
            "something went wrong logging in",
            "ada sesuatu yang tidak kena berlaku semasa log masuk. sila cuba lagi",
            "发生错误，请重试", "発生した問題のため、ログインできませんでした", "문제가 발생했습니다. 다시 시도해 주세요",
            "ha ocurrido un error al iniciar sesión", "erro ao fazer login", "une erreur s'est produite lors de la connexion",
            "si è verificato un problema durante l'accesso", "es ist ein fehler beim anmelden aufgetreten",
            "เกิดข้อผิดพลาดในการเข้าสู่ระบบ", "đã xảy ra sự cố khi đăng nhập",
        ]
        if any(m in error_lower for m in went_wrong_markers):
            return ('error', None, None, 'Something went wrong logging in. Please try again.')
        
        # Rate limit / too many attempts
        rate_limit_markers = [
            "too many requests", "rate limit", "try again later",
            "terlalu banyak permintaan", "buat sementara waktu", "demasiadas solicitudes",
            "muitas solicitações", "zu viele anfragen", "trop de demandes", "troppi tentativi",
            "過多のリクエスト", "요청이 너무 많습니다", "quá nhiều yêu cầu"
        ]
        if any(m in error_lower for m in rate_limit_markers):
            return ('error', None, None, 'Rate limited - Too many requests. Please wait and try again.')
    except Exception:
        pass
    return None

