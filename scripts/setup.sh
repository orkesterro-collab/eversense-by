#!/usr/bin/env bash
# Первичная настройка сайта EVERSENSE.
# Запуск: docker compose run --rm cli
# Скрипт можно запускать повторно: уже сделанные шаги пропускаются.
set -euo pipefail

cd /var/www/html

echo "→ Жду WordPress и базу данных…"
for i in $(seq 1 60); do
  if [ -f wp-config.php ] && wp db check >/dev/null 2>&1; then break; fi
  sleep 2
done

if ! wp core is-installed >/dev/null 2>&1; then
  echo "→ Устанавливаю WordPress"
  wp core install \
    --url="$WP_URL" \
    --title="EVERSENSE" \
    --admin_user="$WP_ADMIN_USER" \
    --admin_password="$WP_ADMIN_PASSWORD" \
    --admin_email="$WP_ADMIN_EMAIL" \
    --skip-email
fi

echo "→ Язык админки и часовой пояс"
wp language core install ru_RU --activate || true
case "${EVERSENSE_COUNTRY:-by}" in
  kz) wp option update timezone_string "Asia/Almaty" ;;
  *)  wp option update timezone_string "Europe/Minsk" ;;
esac

echo "→ Плагины"
wp plugin is-installed polylang || wp plugin install polylang
wp plugin activate polylang
wp language plugin install polylang ru_RU || true

echo "→ Тема EVERSENSE"
wp theme activate eversense

echo "→ Постоянные ссылки"
wp rewrite structure '/%postname%/' --hard

echo "→ Демо-контент: языки, страницы, серии, декоры, дилеры, меню"
wp eversense seed

wp rewrite flush --hard
echo ""
echo "✓ Готово. Сайт: $WP_URL   Админка: $WP_URL/wp-admin  ($WP_ADMIN_USER / $WP_ADMIN_PASSWORD)"
