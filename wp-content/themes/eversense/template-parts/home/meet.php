<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-meet ev-section ev-beige">
	<div class="ev-pattern ev-pattern--soft" aria-hidden="true"></div>
	<div class="ev-container">
		<div class="ev-meet__head" data-reveal>
			<h2 class="ev-display"><?php ev_e( 'meet_title' ); ?></h2>
			<p class="ev-meet__text"><?php ev_e( 'meet_text' ); ?></p>
		</div>

		<div class="ev-meet__grid">
			<div class="ev-meet__dialog" data-reveal>
				<p class="ev-meet__q"><?php ev_e( 'meet_q' ); ?></p>
				<p class="ev-meet__a"><?php ev_e( 'meet_a' ); ?></p>
			</div>

			<div class="ev-meet__wood" data-reveal>
				<div class="ev-wood">
					<div class="ev-wood__half ev-wood__half--aspen">
						<span class="ev-wood__pct">50%</span>
						<span class="ev-wood__name"><?php ev_e( 'wood_aspen' ); ?></span>
					</div>
					<div class="ev-wood__half ev-wood__half--birch">
						<span class="ev-wood__pct">50%</span>
						<span class="ev-wood__name"><?php ev_e( 'wood_birch' ); ?></span>
					</div>
				</div>
				<h3 class="ev-h4"><?php ev_e( 'wood_title' ); ?></h3>
				<p><?php ev_e( 'wood_text' ); ?></p>
			</div>
		</div>
	</div>
</section>
