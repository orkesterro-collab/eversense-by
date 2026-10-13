<?php
/** Запасной шаблон: список записей. */
defined( 'ABSPATH' ) || exit;
get_header();
?>
<section class="ev-section--tight">
	<div class="ev-container ev-container--narrow">
		<h1 class="ev-h1"><?php echo esc_html( wp_strip_all_tags( get_the_archive_title() ) ?: 'EVERSENSE' ); ?></h1>
		<?php if ( have_posts() ) : ?>
			<ul class="ev-post-list">
				<?php
				while ( have_posts() ) :
					the_post();
					?>
					<li><a class="ev-h4" href="<?php the_permalink(); ?>"><?php the_title(); ?></a><?php the_excerpt(); ?></li>
				<?php endwhile; ?>
			</ul>
			<?php the_posts_pagination(); ?>
		<?php endif; ?>
	</div>
</section>
<?php
get_footer();
