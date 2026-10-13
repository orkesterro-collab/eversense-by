<?php
/**
 * EVERSENSE — тема сайта дистрибьютора.
 *
 * Структура:
 *   inc/helpers.php  — язык, страна, тексты, настройки, ссылки
 *   inc/setup.php    — поддержка темы, меню, ассеты, мелочи
 *   inc/content.php  — декоры, серии, дилеры (типы записей и таксономия)
 *   inc/fields.php   — поля в админке (характеристики, дилеры, серии)
 *   inc/options.php  — страница «Внешний вид → Настройки EVERSENSE»
 *   inc/icons.php    — линейные пиктограммы в стиле бренд-бука
 *   inc/seed.php     — команда WP-CLI `wp eversense seed`
 */

defined( 'ABSPATH' ) || exit;

define( 'EV_VERSION', '1.0.0' );
define( 'EV_DIR', get_template_directory() );
define( 'EV_URI', get_template_directory_uri() );

require EV_DIR . '/inc/helpers.php';
require EV_DIR . '/inc/setup.php';
require EV_DIR . '/inc/content.php';
require EV_DIR . '/inc/fields.php';
require EV_DIR . '/inc/options.php';
require EV_DIR . '/inc/icons.php';

if ( defined( 'WP_CLI' ) && WP_CLI ) {
	require EV_DIR . '/inc/seed.php';
}
