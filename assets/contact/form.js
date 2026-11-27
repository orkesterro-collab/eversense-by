(function () {
  'use strict';

  const form = document.getElementById('cooperation-form');
  if (!form) return;

  const submit = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[role="status"]');
  const contact = form.elements.namedItem('contact');
  const emailCheck = document.createElement('input');
  emailCheck.type = 'email';
  if (contact) {
    contact.addEventListener('input', () => contact.setCustomValidity(''));
  }

  form.addEventListener('submit', async function (event) {
    for (const field of form.querySelectorAll('[required]')) {
      field.value = field.value.trim();
    }
    if (contact) {
      const phone = contact.value.replace(/[\p{Zs}\p{Pd}().]/gu, '');
      emailCheck.value = contact.value;
      const valid = emailCheck.validity.valid || /^\+?[0-9]{7,15}$/.test(phone);
      contact.setCustomValidity(valid ? '' : 'Укажите электронную почту или номер телефона для ответа.');
    }
    if (!form.reportValidity()) {
      event.preventDefault();
      return;
    }
    if (!window.fetch || new URL(form.action).origin !== window.location.origin) return;
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
