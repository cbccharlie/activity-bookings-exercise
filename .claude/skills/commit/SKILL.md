---
name: commit
description: Crea commits en la rama develop con Conventional Commits y mensaje en castellano. Úsala siempre que el usuario pida hacer commit, commitear o guardar los cambios en git ("haz un commit de lo que llevamos", "sube esto a develop"), aunque no mencione el formato ni la rama.
---

# Commit en develop

Proyecto de ejercicio con un único desarrollador: sin ramas feature, todo va a `develop`.
Invocar esta skill autoriza el commit (y crear `develop` si falta), pero no el push.

## Pasos

1. **Rama.** Si no estás en `develop`, cámbiate (`git switch develop`) o créala desde la rama
   actual si no existe (`git switch -c develop`). Si git se niega por conflictos con cambios
   locales, para y avisa: nada de `stash` ni descartar cambios por tu cuenta.
2. **Qué entra.** Revisa `git status` y el diff. Si ya hay cambios preparados, respeta esa
   selección; si no, añade por ruta, nunca `git add -A`. Deja fuera secretos y basura, y avisa.
   Un commit por cambio lógico: si el diff mezcla cosas sin relación, haz varios commits. Un
   OpenSpec change completo puede ir en uno solo.
3. **Check.** Si se toca `src/`, `tests/` o `pyproject.toml`, pasa el check completo de AGENTS.md.
   Si falla, pregunta antes de commitear.
4. **Commit** con `git commit -F -` y heredoc, sin `--amend` ni `--no-verify` salvo petición.
5. **Informa** con `git log --oneline` de los commits creados y lo que hayas dejado fuera.

## Mensaje

```
<tipo>(<ámbito>): <asunto>

<cuerpo: qué y por qué>
```

- **Tipo** estándar de Conventional Commits, en inglés (`feat`, `fix`, `refactor`, `test`, `docs`,
  `build` para dependencias y `uv.lock`, `chore`...).
- **Ámbito** opcional: `config`, `auth`, `activities`, `bookings`, `cli`, `api`, `openspec`,
  `claude`. Omítelo si el cambio es transversal.
- **Asunto** en castellano, imperativo y minúscula («añade», «corrige»), sin punto final y con
  ≤ 72 caracteres en total.
- **Cuerpo** en castellano cuando el porqué no sea obvio. Si viene de un OpenSpec change, añade
  el pie `Change: <nombre>`. Si el entorno indica una línea `Co-Authored-By`, ponla al final.

```
feat(auth): añade los comandos register y login con JWT

El token se guarda en la configuración del usuario para reutilizarlo
en las rutas protegidas.

Change: add-auth
```
