<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-solution ev-section">
	<div class="ev-container">
		<div class="ev-solution__head" data-reveal>
			<h2 class="ev-display"><?php ev_e( 'solution_title' ); ?></h2>
			<p class="ev-lead"><?php ev_e( 'solution_text' ); ?></p>
			<a class="ev-btn" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'view_catalog' ); ?></a>
		</div>

		<div class="ev-features" data-slider aria-roledescription="carousel" aria-label="<?php echo esc_attr( ev_t( 'solution_sub_title' ) . ' ' . ev_t( 'solution_sub_text' ) ); ?>">
			<div class="ev-features__intro">
				<h3 class="ev-h3"><?php ev_e( 'solution_sub_title' ); ?> <span class="ev-accent"><?php ev_e( 'solution_sub_text' ); ?></span></h3>
				<div class="ev-arrows">
					<button type="button" class="ev-arrow ev-arrow--dark" data-prev><span class="ev-sr"><?php ev_e( 'prev' ); ?></span><?php echo ev_icon( 'arrow-l' ); // phpcs:ignore ?></button>
					<button type="button" class="ev-arrow ev-arrow--dark" data-next><span class="ev-sr"><?php ev_e( 'next' ); ?></span><?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></button>
				</div>
				<div class="ev-dots ev-dots--dark" data-dots></div>
			</div>
			<div class="ev-features__slides">
				<?php
				$arts  = [ 1 => 'warm', 2 => 'light', 3 => 'rings', 4 => 'dark' ];
				$icons = [ 1 => 'shield', 2 => 'drop', 3 => 'layers', 4 => 'impact' ];
				foreach ( [ 1, 2, 3, 4 ] as $i ) :
					?>
					<article class="ev-feature<?php echo 1 === $i ? ' is-active' : ''; ?>" data-slide>
						<div class="ev-feature__media ev-framed"><?php echo ev_media( 'img_feat_' . $i, $arts[ $i ], '', 'ev-card' ); // phpcs:ignore ?></div>
						<div class="ev-feature__body">
							<?php echo ev_icon( $icons[ $i ], 'ev-feature__icon' ); // phpcs:ignore ?>
							<p class="ev-feature__brand">EVERSENSE.</p>
							<h4 class="ev-h3"><?php ev_e( 'feat_' . $i . '_title' ); ?></h4>
							<p class="ev-feature__lead"><?php ev_e( 'feat_' . $i . '_lead' ); ?></p>
							<p class="ev-feature__text"><?php ev_e( 'feat_' . $i . '_text' ); ?></p>
						</div>
					</article>
				<?php endforeach; ?>
			</div>
		</div>
	</div>
</section>
