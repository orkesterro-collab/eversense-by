(function () {
  'use strict';

  const form = document.getElementById('cooperation-form');
  if (!form || !window.fetch || new URL(form.action).origin !== window.location.origin) return;

  const submit = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[role="status"]');

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (submit.disabled) return;
    submit.disabled = true;
    status.classList.remove('is-error');
    status.textContent = 'Отправляем сообщение…';
    if (location.hash === '#cooperation-sent') {
      history.replaceState(null, '', location.pathname + location.search);
    }

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(form)
      });
      const result = await response.json();
      if (response.ok && result.ok === true) {
        form.reset();
        status.textContent = result.message;
      } else {
        status.classList.add('is-error');
        status.textContent = result.message || 'Не удалось отправить сообщение. Попробуйте ещё раз или позвоните нам.';
      }
    } catch {
      status.classList.add('is-error');
      status.textContent = 'Не удалось подтвердить отправку. Попробуйте позже или позвоните нам.';
    } finally {
      submit.disabled = false;
    }
  });
})();
