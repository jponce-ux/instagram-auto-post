# Especificación: Vista de Confirmación de Registro

## Problema

Actualmente, después de registrarse exitosamente, el usuario es redirigido directamente a `/auth/login?registered=1` donde un toast informa que la cuenta fue creada. Este flujo es confuso porque:

1. El usuario no recibe contexto claro sobre qué hacer después (verificar su email)
2. No hay una página dedicada que comunique el estado de "cuenta creada, pendiente de verificación"
3. El toast desaparece rápidamente y el usuario puede perder la información
4. El usuario es redirigido al login después de registrarse sin entender que debe verificar su email, sin ser notificado de esa dependencia. 

## Historias de Usuario

### HU-1: Página de confirmación post-registro
**Como** usuario recién registrado  
**Quiero** ver una página que me confirme que mi cuenta fue creada y me indique que debo verificar mi email  
**Para** entender qué pasos siguen antes de poder usar la aplicación

#### Criterios de Aceptación

**CA-1.1: Redirección automática post-registro**
- **Dado** que un usuario completa el formulario de registro exitosamente
- **Cuando** el servidor procesa el registro
- **Entonces** el usuario es redirigido a `/auth/confirm-email` automáticamente

**CA-1.2: Contenido informativo de la página**
- **Dado** que el usuario llega a `/auth/confirm-email`
- **Cuando** la página se renderiza
- **Entonces** muestra:
  - Un título claro ("¡Casi listo!" o "Verifica tu correo electrónico")
  - Un icono visual (sobre o check verde)
  - Un mensaje explicando que se envió un email de confirmación
  - Una mención de revisar la carpeta de spam
  - Un botón "Ir al Login" que redirige a `/auth/login`

**CA-1.3: Diseño responsive**
- **Dado** que el usuario accede desde un dispositivo móvil
- **Cuando** la página se renderiza
- **Entonces** el contenido está centrado y legible sin scroll horizontal

**CA-1.4: Consistencia visual**
- **Dado** que la página usa Tailwind CSS
- **Cuando** se compara con las páginas de login y registro
- **Entonces** comparte la misma paleta de colores, tipografía y estilo de componentes

**CA-1.5: Acceso público**
- **Dado** que el usuario no está autenticado
- **Cuando** navega a `/auth/confirm-email`
- **Entonces** puede ver la página sin restricciones

**CA-1.6: Router guard para usuarios autenticados**
- **Dado** que el usuario ya está autenticado
- **Cuando** navega a `/auth/confirm-email`
- **Entonces** es redirigido al dashboard

## No-Objetivos

- Implementar la verificación real del email (esto será TASK-023)
- Generar tokens de verificación en esta iteración
- Reenvío de email de confirmación desde esta página
- Personalización del mensaje con el email del usuario (puede agregarse después)

## Métricas de Éxito

- El 100% de los registros exitosos redirigen a la página de confirmación
- La página carga en menos de 200ms (es solo HTML estático)
- El botón "Ir al Login" funciona correctamente en todos los navegadores soportados

## Preguntas Abiertas

1. ¿Se debe mostrar el email del usuario en la página para confirmar a dónde se envió? (ej: "Enviamos un email a tu***@gmail.com")
2. ¿Se debe agregar un botón de "Reenviar email" en esta iteración o dejarlo para TASK-023?
3. ¿Se debe eliminar el parámetro `?registered=1` del login una vez que esta página exista?
