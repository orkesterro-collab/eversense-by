<?php
/**
 * Линейные пиктограммы: одинаковая толщина линий, без заливки — как в бренд-буке.
 */

defined( 'ABSPATH' ) || exit;

function ev_icon( $name, $class = '' ) {
	$p = [
		'shield'   => '<path d="M24 5 9 10v12c0 9.5 6.3 17.2 15 21 8.7-3.8 15-11.5 15-21V10L24 5Z"/><path d="m17 24 5 5 9-10"/>',
		'layers'   => '<path d="m24 8 18 9-18 9-18-9 18-9Z"/><path d="m6 24 18 9 18-9"/><path d="m6 31 18 9 18-9"/>',
		'drop'     => '<path d="M24 6s-12 13.5-12 22a12 12 0 0 0 24 0C36 19.5 24 6 24 6Z"/><path d="M18.5 29a6 6 0 0 0 5.5 5.5"/>',
		'impact'   => '<circle cx="24" cy="24" r="7"/><path d="M24 5v6M24 37v6M5 24h6M37 24h6M10.6 10.6l4.2 4.2M33.2 33.2l4.2 4.2M10.6 37.4l4.2-4.2M33.2 14.8l4.2-4.2"/>',
		'eye'      => '<path d="M4 24s7-12 20-12 20 12 20 12-7 12-20 12S4 24 4 24Z"/><circle cx="24" cy="24" r="6"/>',
		'hand'     => '<path d="M15 26V12a3 3 0 0 1 6 0v10M21 21V9a3 3 0 0 1 6 0v12M27 21v-9a3 3 0 0 1 6 0v12M33 23v-4a3 3 0 0 1 6 0v8c0 9-6 15-14 15-6 0-9-3-12-8l-5-8a3 3 0 0 1 5-3l3 4"/>',
		'ear'      => '<path d="M14 18a10 10 0 0 1 20 0c0 6-5 8-6 12-1 5-3 10-8 10-3 0-5-2-5-4"/><path d="M19 18a5 5 0 0 1 10 0c0 3-3 4-3 6"/>',
		'leaf'     => '<path d="M10 38C8 22 18 10 40 8c0 20-12 32-26 30"/><path d="M10 38c6-10 14-17 22-22"/>',
		'cycle'    => '<path d="M38 20A15 15 0 0 0 11 15"/><path d="M10 7v8h8"/><path d="M10 28a15 15 0 0 0 27 5"/><path d="M38 41v-8h-8"/>',
		'tree'     => '<path d="M24 42V26"/><path d="M24 6c-8 0-13 6-13 12 0 7 6 10 13 10s13-3 13-10c0-6-5-12-13-12Z"/><path d="M24 30l-5-5M24 26l5-5"/>',
		'cloud'    => '<path d="M14 36h20a8 8 0 0 0 0-16 11 11 0 0 0-21-2 9 9 0 0 0 1 18Z"/><path d="M19 29h3M26 29h3"/>',
		'download' => '<path d="M24 6v24"/><path d="m15 21 9 9 9-9"/><path d="M8 34v6h32v-6"/>',
		'arrow-l'  => '<path d="M40 24H8"/><path d="m18 14-10 10 10 10"/>',
		'arrow-r'  => '<path d="M8 24h32"/><path d="m30 14 10 10-10 10"/>',
		'pin'      => '<path d="M24 43s14-12.5 14-24a14 14 0 0 0-28 0c0 11.5 14 24 14 24Z"/><circle cx="24" cy="19" r="5"/>',
		'phone'    => '<path d="M17 6h-5a4 4 0 0 0-4 4c0 17.7 14.3 32 32 32a4 4 0 0 0 4-4v-5l-8-4-4 4c-5-2-9-6-11-11l4-4-4-8Z"/>',
		'mail'     => '<rect x="6" y="11" width="36" height="26" rx="2"/><path d="m6 13 18 13 18-13"/>',
		'clock'    => '<circle cx="24" cy="24" r="18"/><path d="M24 13v11l7 5"/>',
		'menu'     => '<path d="M6 16h36M6 32h36"/>',
		'close'    => '<path d="m11 11 26 26M37 11 11 37"/>',
		'check'    => '<path d="m10 25 9 9 19-20"/>',
		'list'     => '<path d="M16 12h26M16 24h26M16 36h26"/><circle cx="7" cy="12" r="1.5"/><circle cx="7" cy="24" r="1.5"/><circle cx="7" cy="36" r="1.5"/>',
		'map'      => '<path d="m6 11 12-5 12 5 12-5v31l-12 5-12-5-12 5V11Z"/><path d="M18 6v31M30 11v31"/>',
		'board'    => '<rect x="5" y="17" width="38" height="14" rx="1"/><path d="M15 17v14M33 17v14"/>',
		'ruler'    => '<path d="M6 34 34 6l8 8-28 28-8-8Z"/><path d="m14 26 4 4M19 21l3 3M24 16l4 4M29 11l3 3"/>',
	];
	$social = [
		'telegram'  => '<path d="M41 8 5 22l11 4 3 12 7-8 9 7 6-29Z"/><path d="m16 26 19-12-13 15"/>',
		'instagram' => '<rect x="7" y="7" width="34" height="34" rx="10"/><circle cx="24" cy="24" r="8"/><circle cx="34" cy="14" r="1.5"/>',
		'vk'        => '<path d="M6 15h6c1 6 4 11 7 12V15h6v7c3 0 6-4 7-7h6c-1 5-5 9-8 11 3 1 7 5 8 10h-6c-1-4-4-7-7-7v7h-2C12 36 6 27 6 15Z"/>',
		'facebook'  => '<path d="M27 42V26h6l1-7h-7v-4c0-2 1-4 4-4h3V5h-6c-6 0-8 4-8 9v5h-6v7h6v16"/>',
	];
	$body = $p[ $name ] ?? $social[ $name ] ?? '';
	if ( ! $body ) {
		return '';
	}
	return '<svg class="ev-icon ev-icon--' . esc_attr( $name ) . ' ' . esc_attr( $class ) . '" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' . $body . '</svg>';
}
