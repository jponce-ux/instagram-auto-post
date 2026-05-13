# Especificación: Sistema de Verificación de Email y Tokens de Seguridad

## Problema

Actualmente, los usuarios pueden registrarse e iniciar sesión sin verificar su email. Esto permite:
- Cuentas con emails falsos o inexistentes
- Sin mecanismo de verificación de identidad
- Sin protección contra spam de registro
- El email de bienvenida se envía pero no hay enlace de verificación

## Historias de Usuario

### HU-1: Verificación de email post-registro
**Como** usuario recién registrado  
**Quiero** recibir un email con un enlace de verificación único  
**Para** activar mi cuenta y poder iniciar sesión

#### Criterios de Aceptación

**CA-1.1: Token de verificación generado al registrar**
- **Dado** que un usuario completa el registro exitosamente
- **Cuando** se crea la cuenta
- **Entonces** se genera un token JWT firmado con el user_id y expiración de 20 minutos

**CA-1.2: Email con enlace de verificación**
- **Dado** que se generó un token
- **Cuando** se envía el email de bienvenida
- **Entonces** el email contiene un enlace único: `https://tuapp.com/auth/verify-email/{token}`

**CA-1.3: Endpoint de verificación**
- **Dado** que el usuario hace clic en el enlace del email
- **Cuando** navega a `/auth/verify-email/{token}` con un token válido
- **Entonces** su cuenta se marca como verificada (`is_verified = True`) y es redirigido al login con mensaje de éxito

**CA-1.4: Token expirado**
- **Dado** que el token tiene más de 20 minutos
- **Cuando** el usuario intenta verificar
- **Entonces** es redirigido a `/auth/confirm-email` con mensaje de "Token vencido, solicita uno nuevo"

**CA-1.5: Token inválido o ya usado**
- **Dado** que el token fue manipulado o ya fue utilizado
- **Cuando** el usuario intenta verificar
- **Entonces** es redirigido a `/auth/confirm-email` con mensaje de error

### HU-2: Re-envío de email de verificación
**Como** usuario que no recibió el email de verificación  
**Quiero** poder solicitar un re-envío desde la página de confirmación  
**Para** recibir un nuevo enlace de verificación

#### Criterios de Aceptación

**CA-2.1: Botón de re-envío en confirm-email**
- **Dado** que el usuario está en `/auth/confirm-email`
- **Cuando** hace clic en "¿No recibiste el correo? Reenviar"
- **Entonces** se envía un nuevo email con HTMX sin recargar la página

**CA-2.2: Rate limiting de re-envío**
- **Dado** que el usuario solicitó un re-envío
- **Cuando** intenta solicitar otro dentro de 2 minutos
- **Entonces** recibe un mensaje de "Espera 2 minutos antes de solicitar otro"

**CA-2.3: No re-enviar a usuarios ya verificados**
- **Dado** que el usuario ya verificó su email
- **Cuando** intenta solicitar un re-envío
- **Entonces** recibe un mensaje de "Tu cuenta ya está verificada"

### HU-3: Login requiere email verificado
**Como** sistema de seguridad  
**Quiero** que solo usuarios verificados puedan iniciar sesión  
**Para** prevenir acceso con cuentas no verificadas

#### Criterios de Aceptación

**CA-3.1: Login bloqueado para no verificados**
- **Dado** que un usuario tiene `is_verified = False`
- **Cuando** intenta iniciar sesión
- **Entonces** recibe un mensaje de "Debes verificar tu email antes de iniciar sesión" y es redirigido a `/auth/confirm-email`

**CA-3.2: Login exitoso para verificados**
- **Dado** que un usuario tiene `is_verified = True`
- **Cuando** inicia sesión con credenciales correctas
- **Entonces** accede al dashboard normalmente

## No-Objetivos

- Verificación de email con código OTP (solo enlace)
- Re-verificación periódica del email
- Cambio de email del usuario
- Verificación de email para usuarios existentes no verificados (migración)

## Métricas de Éxito

- 100% de nuevos usuarios requieren verificación para login
- Tokens expiran exactamente a los 20 minutos
- Rate limiting funciona: máximo 1 re-envío cada 2 minutos
- No se generan tokens para usuarios ya verificados

## Preguntas Abiertas

1. ¿Se debe permitir login a usuarios existentes (antes de este cambio) que no tienen `is_verified`?
2. ¿El enlace de verificación debe usar el dominio de Cloudflare Tunnel o configurable?
