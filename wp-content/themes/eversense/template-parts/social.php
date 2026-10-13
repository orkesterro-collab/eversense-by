<?php
defined( 'ABSPATH' ) || exit;
$networks = [
	'telegram'  => 'Telegram',
	'instagram' => 'Instagram',
	'vk'        => 'ВКонтакте',
	'facebook'  => 'Facebook',
];
$links    = array_filter(
	$networks,
	static function ( $k ) {
		return (bool) ev_opt( $k );
	},
	ARRAY_FILTER_USE_KEY
);
if ( ! $links ) {
	return;
}
?>
<ul class="ev-social">
	<?php foreach ( $links as $key => $label ) : ?>
		<li><a href="<?php echo esc_url( ev_opt( $key ) ); ?>" target="_blank" rel="noopener" aria-label="<?php echo esc_attr( $label ); ?>"><?php echo ev_icon( $key ); // phpcs:ignore WordPress.Security.EscapeOutput ?></a></li>
	<?php endforeach; ?>
</ul>
