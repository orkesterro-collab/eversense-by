<?php defined('ABSPATH') || exit; get_header(); while(have_posts()):the_post(); $ids = array_filter(array_map('absint',preg_split('/[;,\s]+/',(string)get_post_meta(get_the_ID(),'ev_gallery_ids',true)))); $codes=preg_split('/\s*[,;]\s*/',(string)get_post_meta(get_the_ID(),'ev_related_codes',true)); ?>
<article class="ev-section--tight"><div class="ev-container">
<p class="ev-eyebrow"><a href="<?php echo esc_url(get_post_type_archive_link('ev_project')); ?>">← <?php echo esc_html(ev_t('menu_projects')); ?></a></p>
<h1 class="ev-display"><?php the_title(); ?></h1>
<?php if(has_post_thumbnail()): ?><div class="ev-project-cover"><?php the_post_thumbnail('ev-wide'); ?></div><?php endif; ?>
<div class="ev-prose"><?php the_content(); ?></div>
<?php if($ids): ?><div class="ev-project-grid"><?php foreach($ids as $img): ?><a href="<?php echo esc_url(wp_get_attachment_url($img)); ?>" target="_blank" rel="noopener"><?php echo wp_get_attachment_image($img,'ev-card',false,['loading'=>'lazy']); ?></a><?php endforeach; ?></div><?php endif; ?>
<h2 class="ev-h3">Использованные декоры</h2>
<div class="ev-project-products">
<?php
$found = false;
foreach ( $codes as $code ) :
	$code = trim( $code );
	if ( ! $code ) { continue; }
	$matches = get_posts( [
		'post_type' => 'ev_decor',
		'posts_per_page' => 1,
		'meta_key' => 'ev_code',
		'meta_value' => $code,
		'suppress_filters' => false,
	] );
	foreach ( $matches as $p ) :
		$found = true;
		?>
		<a class="ev-project-product" href="<?php echo esc_url( get_permalink( $p ) ); ?>">
			<?php echo ev_decor_visual( $p, 'thumbnail' ); // phpcs:ignore ?>
			<span><?php echo esc_html( get_the_title( $p ) ); ?><small><?php echo esc_html( $code ); ?></small></span>
		</a>
	<?php endforeach;
endforeach;
if ( ! $found ) : ?><p>Список декоров уточняется.</p><?php endif; ?>
</div>
</div></article><?php endwhile; get_footer(); ?>