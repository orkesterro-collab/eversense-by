<?php
defined( 'ABSPATH' ) || exit;

/*
 * Схема «разобранной» доски: четыре слоя сверху вниз.
 * Изометрия: верхняя грань — параллелограмм, под ней — торец толщиной t.
 */
$layers = [
	// [ смещение по Y, толщина, класс ]
	[ 40, 6, 'overlay' ],
	[ 120, 8, 'decor' ],
	[ 205, 34, 'core' ],
	[ 352, 10, 'stab' ],
];
$face = static function ( $y, $t ) {
	// Верхняя грань и торцы доски шириной 360 и глубиной 120 в изометрии.
	$top   = sprintf( 'M20 %1$d L220 %2$d L420 %1$d L220 %3$d Z', $y + 60, $y, $y + 120 );
	$left  = sprintf( 'M20 %1$d L220 %2$d L220 %3$d L20 %4$d Z', $y + 60, $y + 120, $y + 120 + $t, $y + 60 + $t );
	$right = sprintf( 'M220 %1$d L420 %2$d L420 %3$d L220 %4$d Z', $y + 120, $y + 60, $y + 60 + $t, $y + 120 + $t );
	return [ $top, $left, $right ];
};
?>
<section class="ev-layers ev-section ev-dark">
	<div class="ev-pattern ev-pattern--dark" aria-hidden="true"></div>
	<div class="ev-container ev-layers__inner">
		<div class="ev-layers__head" data-reveal>
			<h2 class="ev-h2"><?php ev_e( 'layers_title' ); ?></h2>
			<p class="ev-lead"><?php ev_e( 'layers_lead' ); ?></p>
		</div>

		<figure class="ev-layers__figure" data-reveal>
			<svg viewBox="0 0 450 500" role="img" aria-label="<?php echo esc_attr( ev_t( 'layers_title' ) ); ?>">
				<defs>
					<pattern id="ev-grain" width="60" height="14" patternUnits="userSpaceOnUse" patternTransform="skewY(-16.7) rotate(0)">
						<path d="M0 7 Q15 3 30 7 T60 7" fill="none" stroke="#8a6a4c" stroke-width="1" opacity=".55"/>
					</pattern>
					<pattern id="ev-chips" width="10" height="10" patternUnits="userSpaceOnUse">
						<circle cx="2" cy="3" r="1" fill="#a68a6c" opacity=".6"/><circle cx="7" cy="7" r=".8" fill="#8f7559" opacity=".5"/>
					</pattern>
				</defs>
				<?php
				foreach ( array_reverse( $layers, true ) as $n => $l ) :
					[ $top, $left, $right ] = $face( $l[0], $l[1] );
					?>
					<g class="ev-layer ev-layer--<?php echo esc_attr( $l[2] ); ?>">
						<path class="ev-layer__left" d="<?php echo esc_attr( $left ); ?>"/>
						<path class="ev-layer__right" d="<?php echo esc_attr( $right ); ?>"/>
						<path class="ev-layer__top" d="<?php echo esc_attr( $top ); ?>"/>
						<?php if ( 'decor' === $l[2] ) : ?>
							<path d="<?php echo esc_attr( $top ); ?>" fill="url(#ev-grain)"/>
						<?php elseif ( 'core' === $l[2] ) : ?>
							<path d="<?php echo esc_attr( $right ); ?>" fill="url(#ev-chips)"/>
							<path d="<?php echo esc_attr( $left ); ?>" fill="url(#ev-chips)"/>
						<?php endif; ?>
						<circle class="ev-layer__dot" cx="420" cy="<?php echo (int) ( $l[0] + 60 ); ?>" r="4"/>
						<text class="ev-layer__num" x="432" y="<?php echo (int) ( $l[0] + 64 ); ?>"><?php echo (int) ( $n + 1 ); ?></text>
					</g>
				<?php endforeach; ?>
			</svg>
		</figure>

		<ol class="ev-layers__list">
			<?php foreach ( [ 1, 2, 3, 4 ] as $i ) : ?>
				<li class="ev-layers__item" data-reveal>
					<span class="ev-layers__n"><?php echo (int) $i; ?></span>
					<div>
						<h3 class="ev-h4"><?php ev_e( 'layer_' . $i . '_title' ); ?></h3>
						<p><?php ev_e( 'layer_' . $i . '_text' ); ?></p>
					</div>
				</li>
			<?php endforeach; ?>
		</ol>

		<p class="ev-layers__summary" data-reveal><?php ev_e( 'layers_summary' ); ?></p>
	</div>
</section>
