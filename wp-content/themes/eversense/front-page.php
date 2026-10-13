<?php
/**
 * Главная. Блоки повторяют ever-home.ru; каждый блок — отдельный файл
 * в template-parts/home, их можно переставлять или убирать здесь.
 */
defined( 'ABSPATH' ) || exit;

get_header();

foreach (
	[
		'hero',
		'award',
		'balance',
		'meet',
		'senses',
		'solution',
		'layers',
		'collections',
		'eco',
		'textures',
		'trust',
		'contacts',
	] as $block
) {
	get_template_part( 'template-parts/home/' . $block );
}

get_footer();
