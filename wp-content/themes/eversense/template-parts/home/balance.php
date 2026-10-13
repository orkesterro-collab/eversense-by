<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-balance ev-section">
	<div class="ev-container">
		<div class="ev-split">
			<div class="ev-split__text" data-reveal>
				<h2 class="ev-h2"><?php ev_e( 'balance_title' ); ?></h2>
				<p class="ev-lead"><?php ev_e( 'balance_text' ); ?></p>
			</div>
			<div class="ev-split__media ev-framed" data-reveal>
				<?php echo ev_video( 'video_1', 'warm' ); // phpcs:ignore ?>
			</div>
		</div>

		<ul class="ev-stats">
			<?php
			foreach ( [ 1 => 'shield', 2 => 'layers', 3 => 'drop' ] as $i => $icon ) :
				?>
				<li class="ev-stat" data-reveal>
					<?php echo ev_icon( $icon, 'ev-stat__icon' ); // phpcs:ignore ?>
					<span class="ev-stat__value"><?php ev_e( 'stat_' . $i . '_value' ); ?></span>
					<span class="ev-stat__label"><?php ev_e( 'stat_' . $i . '_label' ); ?></span>
				</li>
			<?php endforeach; ?>
		</ul>
	</div>
</section>
