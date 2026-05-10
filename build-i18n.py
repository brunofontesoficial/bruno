#!/usr/bin/env python3
"""
Build script para gerar versões EN e ES estáticas a partir dos HTMLs PT + i18n.js.

Saída:
  /en/<page>.html  — versão inglesa de cada página com data-i18n
  /es/<page>.html  — versão espanhola

Como funciona:
  1. Lê /tmp/i18n.json (extraído de i18n.js via node /tmp/extract_i18n.js)
  2. Para cada HTML PT com data-i18n: gera versões EN e ES
  3. Substitui conteúdo de elementos com data-i18n pela tradução correspondente
  4. Atualiza html lang, title, meta description, canonical, hreflang, og:locale
  5. Atualiza links internos para apontar /en/* e /es/*
  6. Atualiza schema JSON-LD com inLanguage

Roda com: python3 build-i18n.py
"""

import json
import os
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).parent
I18N_JSON = '/tmp/i18n.json'
PAGES_TO_BUILD = [
    'index.html',
    'atleta.html',
    'team-fontes.html',
    'clinicas.html',
    'palestras.html',
    'sailing-experience.html',
    'parceiros.html',
    'eventos.html',
    'coaching-ilca.html',
    'about.html',
]

# Traduções de metadata (title, description, OG) — não estão em data-i18n no HTML
META_TRANSLATIONS = {
    'en': {
        'lang_attr': 'en',
        'og_locale': 'en_US',
        'in_language': 'en',
        # Por página: (title, description, og_title, og_description, twitter_title, twitter_description, og_image_alt)
        'index.html': {
            'title': 'Olympic Performance Coach | Bruno Fontes | World #2',
            'description': 'Olympic performance coach. Transform results as athlete or leader. Method proven through 3× Olympics. Coaching, talks and clinics from Florianópolis.',
            'og_title': 'Bruno Fontes | Official Portal, 3× Olympian, World #2',
            'og_description': 'Sailing coaching, corporate talks, Sailing Experience for executives, on-site clinics and sponsorship partnerships with Bruno Fontes.',
            'twitter_title': 'Bruno Fontes | 3× Olympian · World #2',
            'twitter_description': 'Official portal: coaching, talks, experiences and partnerships.',
            'og_image_alt': 'Bruno Fontes — Olympic performance applied to your case',
        },
        'atleta.html': {
            'title': 'Bruno Fontes — 3× Olympian, World Master Champion 2025',
            'description': 'Olympic athlete profile: Beijing 2008, London 2012, Paris 2024. World #2 ranking, 8× Brazilian champion, 4× South American champion, ILCA Master World Champion 2025.',
            'og_title': 'Bruno Fontes | The Athlete: 3× Olympics, World #2',
            'og_description': 'Career, titles and legacy of a 3× Olympian and ILCA Master World Champion 2025.',
            'twitter_title': 'Bruno Fontes — 3× Olympian',
            'twitter_description': '3× Olympics, 8× Brazilian champion, ILCA Master World Champion 2025.',
            'og_image_alt': 'Bruno Fontes, Olympic athlete',
        },
        'team-fontes.html': {
            'title': 'Team Fontes — Online Sailing Coaching from US$100/mo | Bruno Fontes',
            'description': 'Personalized online sailing coaching with a 3× Olympian. Boat handling, strategy, fitness, mindset and nutrition for ILCA athletes worldwide. Plans from US$100/month.',
            'og_title': 'Team Fontes | Personal Olympic-Level Sailing Coaching',
            'og_description': 'Online sailing coaching with Bruno Fontes, 3× Olympian. From US$100/month — boat handling, tactics, fitness, mindset.',
            'twitter_title': 'Team Fontes — Olympic Sailing Coaching',
            'twitter_description': 'Online sailing coaching from US$100/mo. Olympic method.',
            'og_image_alt': 'Team Fontes — online sailing coaching',
        },
        'clinicas.html': {
            'title': 'Sailing Clinics with a 3× Olympian | Bruno Fontes',
            'description': 'On-site sailing clinics anywhere in the world. Express (1 day), weekend camp (2-3 days) or Olympic week (5-7 days). Groups of 5 to 26+ athletes. Request a proposal.',
            'og_title': 'On-Site Sailing Clinics with Bruno Fontes',
            'og_description': 'Bruno comes to you. 3 formats from 1 day to a full Olympic week, anywhere in the world.',
            'twitter_title': 'Sailing Clinics — Bruno Fontes',
            'twitter_description': 'On-site sailing clinics with a 3× Olympian, anywhere in the world.',
            'og_image_alt': 'Bruno Fontes coaching on the water',
        },
        'palestras.html': {
            'title': 'Keynote Speaker — "Navigating to Success" | Bruno Fontes',
            'description': '40 years of high performance condensed into 1 hour. Resilience, discipline and winning mindset for corporate audiences. Available in PT, EN and ES.',
            'og_title': 'Bruno Fontes — Olympic Keynote Speaker',
            'og_description': 'Corporate keynote: 40 years of high performance, resilience and winning mindset, by a 3× Olympian.',
            'twitter_title': 'Bruno Fontes — Keynote Speaker',
            'twitter_description': '40 years of high performance in 1 hour. Olympic keynote.',
            'og_image_alt': 'Bruno Fontes giving a keynote talk',
        },
        'sailing-experience.html': {
            'title': 'Sailing Experience for Executives & Teams | Bruno Fontes',
            'description': 'A full immersive sailing day in Florianópolis with a 3× Olympian. Designed for executives, leaders and high-performance teams. From the pier to the boardroom.',
            'og_title': 'Sailing Experience — From the Pier to the Boardroom',
            'og_description': 'Immersive sailing day with a 3× Olympian for executives and high-performance teams.',
            'twitter_title': 'Sailing Experience — Bruno Fontes',
            'twitter_description': 'Sailing day with a 3× Olympian for executives.',
            'og_image_alt': 'Bruno Fontes sailing with executives',
        },
        'parceiros.html': {
            'title': 'Partnerships — Sponsor, Ambassador, Influencer | Bruno Fontes',
            'description': 'Three partnership formats with Bruno Fontes — sponsorship, brand ambassador and influencer — for brands that want association with elite Olympic performance.',
            'og_title': 'Bruno Fontes — Brand Partnerships',
            'og_description': 'Sponsorship, ambassador and influencer formats with a 3× Olympian.',
            'twitter_title': 'Partner with Bruno Fontes',
            'twitter_description': 'Brand partnerships with a 3× Olympian.',
            'og_image_alt': 'Bruno Fontes — partnerships',
        },
        'eventos.html': {
            'title': 'ILCA World Championship Aarhus 2026 — Coaching | Bruno Fontes',
            'description': 'Exclusive coaching for athletes competing at the ILCA World Championship in Aarhus 2026. Pre-event training and on-water support during the regatta.',
            'og_title': 'ILCA Worlds Aarhus 2026 — Olympic Coaching',
            'og_description': 'Exclusive coaching for ILCA Worlds 2026 in Aarhus.',
            'twitter_title': 'ILCA Worlds Aarhus 2026 — Coaching',
            'twitter_description': 'Olympic coaching for ILCA Worlds 2026.',
            'og_image_alt': 'ILCA World Championship coaching',
        },
        'coaching-ilca.html': {
            'title': 'ILCA Tactical Guide — Olympic-Level Sailing | Bruno Fontes',
            'description': 'Tactical guide for ILCA 7, ILCA 6 and ILCA 4 sailors, based on 40 years of high performance and 3 Olympic Games. Boat handling, strategy and mindset.',
            'og_title': 'ILCA Tactical Guide — Bruno Fontes',
            'og_description': 'Tactical guide for ILCA sailors by a 3× Olympian.',
            'twitter_title': 'ILCA Tactical Guide',
            'twitter_description': 'Tactical guide for ILCA sailors by a 3× Olympian.',
            'og_image_alt': 'Bruno Fontes ILCA tactical guide',
        },
        'about.html': {
            'title': 'About Bruno Fontes — 3× Olympian & Olympic Coach',
            'description': 'About Bruno Fontes: Olympic athlete (Beijing 2008, London 2012, Paris 2024), Olympic coach (Trinidad & Tobago, China), ILCA Master World Champion 2025.',
            'og_title': 'About Bruno Fontes',
            'og_description': '3× Olympian, Olympic coach, World #2, ILCA Master World Champion 2025.',
            'twitter_title': 'About Bruno Fontes',
            'twitter_description': '3× Olympian, Olympic coach, World #2.',
            'og_image_alt': 'Bruno Fontes — about',
        },
    },
    'es': {
        'lang_attr': 'es',
        'og_locale': 'es_ES',
        'in_language': 'es',
        'index.html': {
            'title': 'Coach de Rendimiento Olímpico | Bruno Fontes | #2 del Mundo',
            'description': 'Coach de rendimiento olímpico. Transforma tus resultados como atleta o líder. Método probado en 3× Olimpiadas. Coaching, charlas y clínicas desde Florianópolis.',
            'og_title': 'Bruno Fontes | Portal Oficial, 3× Olímpico, #2 del Mundo',
            'og_description': 'Coaching de vela, charlas corporativas, Sailing Experience para ejecutivos, clínicas presenciales y patrocinios con Bruno Fontes.',
            'twitter_title': 'Bruno Fontes | 3× Olímpico · #2 del Mundo',
            'twitter_description': 'Portal oficial: coaching, charlas, experiencias y partnerships.',
            'og_image_alt': 'Bruno Fontes — Rendimiento olímpico aplicado a tu caso',
        },
        'atleta.html': {
            'title': 'Bruno Fontes — 3× Olímpico, Campeón del Mundo Master 2025',
            'description': 'Perfil del atleta olímpico: Pekín 2008, Londres 2012, París 2024. Ranking mundial #2, 8× campeón brasileño, 4× campeón sudamericano, Campeón del Mundo Master ILCA 2025.',
            'og_title': 'Bruno Fontes | El Atleta: 3× Olimpiadas, #2 del Mundo',
            'og_description': 'Carrera, títulos y legado de un 3× Olímpico y Campeón del Mundo Master ILCA 2025.',
            'twitter_title': 'Bruno Fontes — 3× Olímpico',
            'twitter_description': '3× Olimpiadas, 8× campeón brasileño, Campeón del Mundo Master ILCA 2025.',
            'og_image_alt': 'Bruno Fontes, atleta olímpico',
        },
        'team-fontes.html': {
            'title': 'Team Fontes — Coaching Online de Vela desde US$100/mes | Bruno Fontes',
            'description': 'Coaching personalizado online con un 3× Olímpico. Boat handling, estrategia, fitness, mindset y nutrición para atletas ILCA en todo el mundo. Desde US$100/mes.',
            'og_title': 'Team Fontes | Coaching Personal Nivel Olímpico',
            'og_description': 'Coaching online de vela con Bruno Fontes, 3× Olímpico. Desde US$100/mes.',
            'twitter_title': 'Team Fontes — Coaching Olímpico de Vela',
            'twitter_description': 'Coaching online desde US$100/mes. Método olímpico.',
            'og_image_alt': 'Team Fontes — coaching online de vela',
        },
        'clinicas.html': {
            'title': 'Clínicas de Vela con un 3× Olímpico | Bruno Fontes',
            'description': 'Clínicas presenciales de vela en cualquier parte del mundo. Express (1 día), weekend camp (2-3 días) o semana olímpica (5-7 días). Grupos de 5 a 26+ atletas.',
            'og_title': 'Clínicas Presenciales con Bruno Fontes',
            'og_description': 'Bruno va a ti. 3 formatos: 1 día, 2-3 días o semana olímpica completa.',
            'twitter_title': 'Clínicas de Vela — Bruno Fontes',
            'twitter_description': 'Clínicas presenciales con un 3× Olímpico, en cualquier parte del mundo.',
            'og_image_alt': 'Bruno Fontes coacheando en el agua',
        },
        'palestras.html': {
            'title': 'Charla Corporativa "Navegando al Éxito" | Bruno Fontes',
            'description': '40 años de alto rendimiento condensados en 1 hora. Resiliencia, disciplina y mentalidad ganadora para audiencias corporativas. Disponible en PT, EN y ES.',
            'og_title': 'Bruno Fontes — Conferencista Olímpico',
            'og_description': 'Charla corporativa: 40 años de alto rendimiento, resiliencia y mentalidad ganadora.',
            'twitter_title': 'Bruno Fontes — Conferencista',
            'twitter_description': '40 años de alto rendimiento en 1 hora. Charla olímpica.',
            'og_image_alt': 'Bruno Fontes dando una charla',
        },
        'sailing-experience.html': {
            'title': 'Sailing Experience para Ejecutivos y Equipos | Bruno Fontes',
            'description': 'Día inmersivo de vela en Florianópolis con un 3× Olímpico. Para ejecutivos, líderes y equipos de alto desempeño. Del muelle al boardroom.',
            'og_title': 'Sailing Experience — Del Muelle al Boardroom',
            'og_description': 'Día de vela con un 3× Olímpico para ejecutivos y equipos de alto desempeño.',
            'twitter_title': 'Sailing Experience — Bruno Fontes',
            'twitter_description': 'Día de vela con un 3× Olímpico para ejecutivos.',
            'og_image_alt': 'Bruno Fontes navegando con ejecutivos',
        },
        'parceiros.html': {
            'title': 'Patrocinios — Sponsor, Embajador, Influencer | Bruno Fontes',
            'description': 'Tres formatos de partnership con Bruno Fontes — patrocinio, embajador de marca e influencer — para marcas que buscan asociación con desempeño olímpico de elite.',
            'og_title': 'Bruno Fontes — Partnerships de Marca',
            'og_description': 'Patrocinio, embajador e influencer con un 3× Olímpico.',
            'twitter_title': 'Patrocinar a Bruno Fontes',
            'twitter_description': 'Partnerships de marca con un 3× Olímpico.',
            'og_image_alt': 'Bruno Fontes — partnerships',
        },
        'eventos.html': {
            'title': 'Mundial ILCA Aarhus 2026 — Coaching | Bruno Fontes',
            'description': 'Coaching exclusivo para atletas que disputan el Campeonato Mundial ILCA en Aarhus 2026. Entrenamiento previo y soporte en agua durante la regata.',
            'og_title': 'Mundial ILCA Aarhus 2026 — Coaching Olímpico',
            'og_description': 'Coaching exclusivo para el Mundial ILCA 2026 en Aarhus.',
            'twitter_title': 'Mundial ILCA Aarhus 2026 — Coaching',
            'twitter_description': 'Coaching olímpico para el Mundial ILCA 2026.',
            'og_image_alt': 'Coaching Mundial ILCA',
        },
        'coaching-ilca.html': {
            'title': 'Guía Táctica ILCA — Vela Nivel Olímpico | Bruno Fontes',
            'description': 'Guía táctica para veleristas de ILCA 7, ILCA 6 e ILCA 4, basada en 40 años de alto rendimiento y 3 Juegos Olímpicos. Boat handling, estrategia y mindset.',
            'og_title': 'Guía Táctica ILCA — Bruno Fontes',
            'og_description': 'Guía táctica para veleristas ILCA por un 3× Olímpico.',
            'twitter_title': 'Guía Táctica ILCA',
            'twitter_description': 'Guía táctica para veleristas ILCA por un 3× Olímpico.',
            'og_image_alt': 'Bruno Fontes guía táctica ILCA',
        },
        'about.html': {
            'title': 'Sobre Bruno Fontes — 3× Olímpico y Coach Olímpico',
            'description': 'Sobre Bruno Fontes: atleta olímpico (Pekín 2008, Londres 2012, París 2024), coach olímpico (Trinidad y Tobago, China), Campeón del Mundo Master ILCA 2025.',
            'og_title': 'Sobre Bruno Fontes',
            'og_description': '3× Olímpico, coach olímpico, #2 del mundo, Campeón Master ILCA 2025.',
            'twitter_title': 'Sobre Bruno Fontes',
            'twitter_description': '3× Olímpico, coach olímpico, #2 del mundo.',
            'og_image_alt': 'Bruno Fontes — sobre',
        },
    },
}

# Mapa de page → URL canônica (sem .html)
PAGE_TO_URL = {
    'index.html': '',
    'atleta.html': 'atleta',
    'team-fontes.html': 'team-fontes',
    'clinicas.html': 'clinicas',
    'palestras.html': 'palestras',
    'sailing-experience.html': 'sailing-experience',
    'parceiros.html': 'parceiros',
    'eventos.html': 'eventos',
    'coaching-ilca.html': 'coaching-ilca',
    'about.html': 'about',
}

INTERNAL_PATHS = list(PAGE_TO_URL.values()) + ['treino', 'guia-4-pilares', 'contato', 'privacidade', 'obrigado-treino']


def translate_html(html: str, lang: str, page: str, translations: dict) -> str:
    """Traduz um HTML PT para EN ou ES."""
    soup = BeautifulSoup(html, 'html.parser')
    meta = META_TRANSLATIONS[lang][page]

    # 1. <html lang>
    if soup.html:
        soup.html['lang'] = META_TRANSLATIONS[lang]['lang_attr']

    # 2. <title>
    if soup.title:
        soup.title.string = meta['title']

    # 3. Meta tags
    def set_meta(soup, attr, name_or_property, content):
        tag = soup.find('meta', {attr: name_or_property})
        if tag:
            tag['content'] = content

    set_meta(soup, 'name', 'description', meta['description'])
    set_meta(soup, 'property', 'og:title', meta['og_title'])
    set_meta(soup, 'property', 'og:description', meta['og_description'])
    set_meta(soup, 'property', 'og:locale', META_TRANSLATIONS[lang]['og_locale'])
    set_meta(soup, 'property', 'og:image:alt', meta['og_image_alt'])
    set_meta(soup, 'name', 'twitter:title', meta['twitter_title'])
    set_meta(soup, 'name', 'twitter:description', meta['twitter_description'])

    # 4. og:url, canonical → apontar pra URL própria do idioma
    page_path = PAGE_TO_URL[page]
    own_url = f'https://brunofontes.com/{lang}/{page_path}' if page_path else f'https://brunofontes.com/{lang}/'
    set_meta(soup, 'property', 'og:url', own_url)
    canonical = soup.find('link', {'rel': 'canonical'})
    if canonical:
        canonical['href'] = own_url

    # 5. hreflang — atualizar pras 3 URLs reais
    pt_url = f'https://brunofontes.com/{page_path}' if page_path else 'https://brunofontes.com/'
    en_url = f'https://brunofontes.com/en/{page_path}' if page_path else 'https://brunofontes.com/en/'
    es_url = f'https://brunofontes.com/es/{page_path}' if page_path else 'https://brunofontes.com/es/'
    for link in soup.find_all('link', {'rel': 'alternate'}):
        if link.get('hreflang') == 'pt-BR':
            link['href'] = pt_url
        elif link.get('hreflang') == 'en':
            link['href'] = en_url
        elif link.get('hreflang') == 'es':
            link['href'] = es_url
        elif link.get('hreflang') == 'x-default':
            link['href'] = pt_url

    # 6. Substituir conteúdo de elementos com data-i18n
    missing = []
    for el in soup.find_all(attrs={'data-i18n': True}):
        key = el['data-i18n']
        if key in translations[lang]:
            new_html = translations[lang][key]
            # Limpar conteúdo atual
            el.clear()
            # Inserir novo HTML como string parseada
            new_soup = BeautifulSoup(new_html, 'html.parser')
            for child in list(new_soup.contents):
                el.append(child)
        else:
            missing.append(key)

    # 7. Atualizar links internos /atleta → /en/atleta
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Apenas links absolutos relativos (começam com /)
        if href.startswith('/') and not href.startswith('//'):
            # Strip leading /, take first segment
            stripped = href.lstrip('/').split('/')[0].split('?')[0].split('#')[0]
            if stripped in INTERNAL_PATHS:
                a['href'] = f'/{lang}{href}'

    # 8. JSON-LD: adicionar inLanguage
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            def add_lang(d):
                if isinstance(d, dict):
                    if '@type' in d and d.get('@type') in ('Person', 'WebPage', 'WebSite', 'FAQPage', 'Article', 'SportsOrganization', 'VideoObject'):
                        d.setdefault('inLanguage', META_TRANSLATIONS[lang]['in_language'])
                    for v in d.values():
                        add_lang(v)
                elif isinstance(d, list):
                    for v in d:
                        add_lang(v)
            add_lang(data)
            script.string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        except (json.JSONDecodeError, TypeError):
            pass

    # 9. Adicionar comentário no topo identificando a versão
    comment_text = f' Auto-generated from /{page} via build-i18n.py — DO NOT EDIT directly. Lang: {lang.upper()} '
    if soup.html:
        from bs4 import Comment
        soup.html.insert(0, Comment(comment_text))

    if missing:
        print(f"    [WARN] {len(missing)} keys faltando: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    return str(soup)


def main():
    if not Path(I18N_JSON).exists():
        print(f"ERRO: {I18N_JSON} não existe. Rode primeiro: node /tmp/extract_i18n.js")
        sys.exit(1)

    with open(I18N_JSON) as f:
        translations = json.load(f)

    print(f"Carregadas traduções: {list(translations.keys())} ({len(translations['pt'])} keys cada)")
    print()

    for lang in ('en', 'es'):
        out_dir = ROOT / lang
        out_dir.mkdir(exist_ok=True)
        print(f"=== Gerando /{lang}/ ===")
        for page in PAGES_TO_BUILD:
            src = ROOT / page
            if not src.exists():
                print(f"  [SKIP] {page} não existe")
                continue
            html = src.read_text(encoding='utf-8')
            translated = translate_html(html, lang, page, translations)
            dst = out_dir / page
            dst.write_text(translated, encoding='utf-8')
            size_orig = src.stat().st_size
            size_new = dst.stat().st_size
            print(f"  ✓ {page} → /{lang}/{page} ({size_orig // 1024}KB → {size_new // 1024}KB)")
        print()


if __name__ == '__main__':
    main()
