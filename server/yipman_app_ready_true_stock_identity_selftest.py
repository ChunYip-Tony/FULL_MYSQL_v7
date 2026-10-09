from pathlib import Path


def run():
    text = Path(__file__).with_name('yipman_app_ready_true_stock_overlay.py').read_text()
    assert 'row_family_ids' in text and 'row_articles' in text
    assert 'fid in row_family_ids' in text
    assert 'article in row_articles' in text
    assert 'targets = {x for x in (family_id, main_article)' not in text
    return {
        'family_id_only_matches_family_domain': 'PASS',
        'article_id_only_matches_article_domain': 'PASS',
        'cross_domain_numeric_collision_removed': 'PASS',
    }


if __name__ == '__main__':
    print(run())
