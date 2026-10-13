<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-eco ev-section ev-beige">
	<div class="ev-container">
		<div class="ev-eco__top">
			<h2 class="ev-h2" data-reveal><?php ev_e( 'eco_title' ); ?></h2>
			<div class="ev-eco__media ev-framed" data-reveal><?php echo ev_media( 'img_eco', 'rings', '', 'ev-wide' ); // phpcs:ignore ?></div>
		</div>
		<ul class="ev-eco__grid">
			<?php foreach ( [ 1 => 'tree', 2 => 'leaf', 3 => 'cycle', 4 => 'cloud' ] as $i => $icon ) : ?>
				<li class="ev-eco__item" data-reveal>
					<?php echo ev_icon( $icon, 'ev-eco__icon' ); // phpcs:ignore ?>
					<h3 class="ev-h4"><?php ev_e( 'eco_' . $i . '_title' ); ?></h3>
					<p><?php ev_e( 'eco_' . $i . '_text' ); ?></p>
				</li>
			<?php endforeach; ?>
		</ul>
	</div>
</section>
