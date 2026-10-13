<?php
/**
 * Template Name: Где купить
 * Магазины партнёров: список по городам и карта (Яндекс Карты).
 */
defined( 'ABSPATH' ) || exit;
get_header();

$dealers = get_posts(
	[
		'post_type'   => 'ev_dealer',
		'numberposts' => -1,
		'orderby'     => [ 'menu_order' => 'ASC', 'title' => 'ASC' ],
	]
);
$cities  = [];
$points  = [];
foreach ( $dealers as $d ) {
	$city              = get_post_meta( $d->ID, 'ev_city', true ) ?: '—';
	$cities[ $city ][] = $d;
	$lat               = (float) str_replace( ',', '.', (string) get_post_meta( $d->ID, 'ev_lat', true ) );
	$lng               = (float) str_replace( ',', '.', (string) get_post_meta( $d->ID, 'ev_lng', true ) );
	if ( $lat && $lng ) {
		$points[] = [
			'id'      => $d->ID,
			'title'   => get_the_title( $d ),
			'city'    => $city,
			'address' => (string) get_post_meta( $d->ID, 'ev_address', true ),
			'phone'   => (string) get_post_meta( $d->ID, 'ev_phone', true ),
			'hours'   => (string) get_post_meta( $d->ID, 'ev_hours', true ),
			'site'    => (string) get_post_meta( $d->ID, 'ev_site', true ),
			'coords'  => [ $lat, $lng ],
		];
	}
}
ksort( $cities, SORT_STRING );
$map = [
	'center' => ev_country( 'map_center' ),
	'zoom'   => ev_country( 'map_zoom' ),
	'points' => $points,
	'i18n'   => [ 'site' => ev_t( 'where_site' ), 'hours' => ev_t( 'where_hours' ) ],
];
?>
<section class="ev-page-head ev-section--tight">
	<div class="ev-container">
		<?php get_template_part( 'template-parts/breadcrumbs', null, [ 'items' => [ [ get_the_title(), null ] ] ] ); ?>
		<h1 class="ev-display"><?php ev_e( 'where_title' ); ?></h1>
		<?php
		while ( have_posts() ) :
			the_post();
			if ( get_the_content() ) :
				?>
				<div class="ev-prose"><?php the_content(); ?></div>
				<?php
			endif;
		endwhile;
		?>
	</div>
</section>

<section class="ev-where ev-section--tight" data-where>
	<div class="ev-container">
		<?php if ( ! $dealers ) : ?>
			<div class="ev-empty">
				<p><?php ev_e( 'where_empty' ); ?></p>
				<a class="ev-btn" href="<?php echo esc_url( ev_home_url( '#contacts' ) ); ?>"><?php ev_e( 'menu_contacts' ); ?></a>
			</div>
		<?php else : ?>
			<div class="ev-where__bar">
				<div class="ev-toggle" role="tablist">
					<button type="button" class="ev-toggle__btn is-active" role="tab" aria-selected="true" data-view="list"><?php echo ev_icon( 'list' ); // phpcs:ignore ?> <?php ev_e( 'where_list' ); ?></button>
					<button type="button" class="ev-toggle__btn" role="tab" aria-selected="false" data-view="map"><?php echo ev_icon( 'map' ); // phpcs:ignore ?> <?php ev_e( 'where_map' ); ?></button>
				</div>
				<?php if ( count( $cities ) > 1 ) : ?>
					<label class="ev-select">
						<span class="ev-sr"><?php ev_e( 'where_city' ); ?></span>
						<select data-city>
							<option value=""><?php ev_e( 'where_all_cities' ); ?></option>
							<?php foreach ( array_keys( $cities ) as $c ) : ?>
								<option value="<?php echo esc_attr( $c ); ?>"><?php echo esc_html( $c ); ?></option>
							<?php endforeach; ?>
						</select>
					</label>
				<?php endif; ?>
			</div>

			<div class="ev-where__list" data-panel="list">
				<?php foreach ( $cities as $city => $list ) : ?>
					<div class="ev-city" data-city-group="<?php echo esc_attr( $city ); ?>">
						<h2 class="ev-h3"><?php echo esc_html( $city ); ?></h2>
						<ul class="ev-dealers">
							<?php foreach ( $list as $d ) : ?>
								<?php
								$phone = get_post_meta( $d->ID, 'ev_phone', true );
								$site  = get_post_meta( $d->ID, 'ev_site', true );
								$hours = get_post_meta( $d->ID, 'ev_hours', true );
								$email = get_post_meta( $d->ID, 'ev_email', true );
								$addr  = get_post_meta( $d->ID, 'ev_address', true );
								?>
								<li class="ev-dealer">
									<h3 class="ev-dealer__name"><?php echo esc_html( get_the_title( $d ) ); ?></h3>
									<?php if ( $addr ) : ?>
										<p class="ev-dealer__row"><?php echo ev_icon( 'pin' ); // phpcs:ignore ?><a href="<?php echo esc_url( 'https://yandex.by/maps/?text=' . rawurlencode( $city . ', ' . $addr ) ); ?>" target="_blank" rel="noopener"><?php echo esc_html( $addr ); ?></a></p>
									<?php endif; ?>
									<?php if ( $phone ) : ?>
										<p class="ev-dealer__row"><?php echo ev_icon( 'phone' ); // phpcs:ignore ?><a href="<?php echo esc_attr( ev_tel( $phone ) ); ?>"><?php echo esc_html( $phone ); ?></a></p>
									<?php endif; ?>
									<?php if ( $email ) : ?>
										<p class="ev-dealer__row"><?php echo ev_icon( 'mail' ); // phpcs:ignore ?><a href="mailto:<?php echo esc_attr( $email ); ?>"><?php echo esc_html( $email ); ?></a></p>
									<?php endif; ?>
									<?php if ( $hours ) : ?>
										<p class="ev-dealer__row"><?php echo ev_icon( 'clock' ); // phpcs:ignore ?><span><?php echo esc_html( $hours ); ?></span></p>
									<?php endif; ?>
									<?php if ( $site ) : ?>
										<p class="ev-dealer__row"><?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?><a href="<?php echo esc_url( $site ); ?>" target="_blank" rel="noopener"><?php echo esc_html( wp_parse_url( $site, PHP_URL_HOST ) ?: $site ); ?></a></p>
									<?php endif; ?>
								</li>
							<?php endforeach; ?>
						</ul>
					</div>
				<?php endforeach; ?>
			</div>

			<div class="ev-where__map ev-framed" data-panel="map" hidden>
				<div id="ev-map" class="ev-map"></div>
			</div>
			<script type="application/json" id="ev-map-data"><?php echo wp_json_encode( $map, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP ); ?></script>
		<?php endif; ?>
	</div>
</section>
<?php
get_footer();
