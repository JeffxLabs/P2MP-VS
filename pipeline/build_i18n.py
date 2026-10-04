#!/usr/bin/env python3
"""Generate file://-compatible translated UI and stage data.

Run python3 pipeline/build_i18n.py after editing this file or competition_stages.json.
Every locale owns every string; placeholders are validated before writing.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {'en': 'en-US', 'fr': 'fr-FR', 'ru': 'ru-RU', 'tr': 'tr-TR', 'pl': 'pl-PL', 'es': 'es-ES', 'pt': 'pt-PT', 'de': 'de-DE', 'ko': 'ko-KR', 'zh': 'zh-CN'}
NAMES = {'en': 'English', 'fr': 'Français', 'ru': 'Русский', 'tr': 'Türkçe', 'pl': 'Polski', 'es': 'Español', 'pt': 'Português', 'de': 'Deutsch', 'ko': '한국어', 'zh': '简体中文'}

# Shared label translations follow the sister Capitol site.
T = {
  "en": {
    "overview": "Overview",
    "members": "Members",
    "opponent": "Opponent",
    "trends": "Trends",
    "data": "Data",
    "language": "Language",
    "skip": "Skip to content",
    "copy_link": "Copy link",
    "copied": "Link copied",
    "theme_light": "Switch to day mode",
    "theme_dark": "Switch to night mode",
    "points": "Points",
    "rank": "Rank",
    "tier": "Tier",
    "active_only": "Active players only",
    "download_csv": "Download CSV",
    "close": "Close",
    "no_results": "No matches",
    "depth": "Points by rank tier",
    "expand": "Chart and table",
    "difference": "Difference",
    "total": "Total points",
    "methodology": "How the data is collected"
  },
  "fr": {
    "overview": "Aperçu",
    "members": "Membres",
    "opponent": "Adversaire",
    "trends": "Tendances",
    "data": "Données",
    "language": "Langue",
    "skip": "Aller au contenu",
    "copy_link": "Copier le lien",
    "copied": "Lien copié",
    "theme_light": "Passer en mode jour",
    "theme_dark": "Passer en mode nuit",
    "points": "Points",
    "rank": "Rang",
    "tier": "Tranche",
    "active_only": "Joueurs actifs uniquement",
    "download_csv": "Télécharger le CSV",
    "close": "Fermer",
    "no_results": "Aucun résultat",
    "depth": "Points par tranche de rang",
    "expand": "Graphique et tableau",
    "difference": "Écart",
    "total": "Points totaux",
    "methodology": "Comment les données sont collectées"
  },
  "ru": {
    "overview": "Обзор",
    "members": "Участники",
    "opponent": "Противник",
    "trends": "Динамика",
    "data": "Данные",
    "language": "Язык",
    "skip": "Перейти к содержимому",
    "copy_link": "Копировать ссылку",
    "copied": "Ссылка скопирована",
    "theme_light": "Дневной режим",
    "theme_dark": "Ночной режим",
    "points": "Очки",
    "rank": "Место",
    "tier": "Группа",
    "active_only": "Только активные игроки",
    "download_csv": "Скачать CSV",
    "close": "Закрыть",
    "no_results": "Ничего не найдено",
    "depth": "Очки по группам мест",
    "expand": "График и таблица",
    "difference": "Разница",
    "total": "Всего очков",
    "methodology": "Как собираются данные"
  },
  "tr": {
    "overview": "Genel bakış",
    "members": "Üyeler",
    "opponent": "Rakip",
    "trends": "Eğilimler",
    "data": "Veri",
    "language": "Dil",
    "skip": "İçeriğe geç",
    "copy_link": "Bağlantıyı kopyala",
    "copied": "Bağlantı kopyalandı",
    "theme_light": "Gündüz moduna geç",
    "theme_dark": "Gece moduna geç",
    "points": "Puan",
    "rank": "Sıra",
    "tier": "Dilim",
    "active_only": "Yalnızca aktif oyuncular",
    "download_csv": "CSV indir",
    "close": "Kapat",
    "no_results": "Sonuç yok",
    "depth": "Sıra dilimine göre puan",
    "expand": "Grafik ve tablo",
    "difference": "Fark",
    "total": "Toplam puan",
    "methodology": "Veriler nasıl toplanır"
  },
  "pl": {
    "overview": "Przegląd",
    "members": "Członkowie",
    "opponent": "Przeciwnik",
    "trends": "Trendy",
    "data": "Dane",
    "language": "Język",
    "skip": "Przejdź do treści",
    "copy_link": "Kopiuj link",
    "copied": "Skopiowano link",
    "theme_light": "Tryb dzienny",
    "theme_dark": "Tryb nocny",
    "points": "Punkty",
    "rank": "Miejsce",
    "tier": "Przedział",
    "active_only": "Tylko aktywni gracze",
    "download_csv": "Pobierz CSV",
    "close": "Zamknij",
    "no_results": "Brak wyników",
    "depth": "Punkty według przedziałów miejsc",
    "expand": "Wykres i tabela",
    "difference": "Różnica",
    "total": "Łączne punkty",
    "methodology": "Jak zbierane są dane"
  },
  "es": {
    "overview": "Resumen",
    "members": "Miembros",
    "opponent": "Rival",
    "trends": "Tendencias",
    "data": "Datos",
    "language": "Idioma",
    "skip": "Saltar al contenido",
    "copy_link": "Copiar enlace",
    "copied": "Enlace copiado",
    "theme_light": "Cambiar a modo día",
    "theme_dark": "Cambiar a modo noche",
    "points": "Puntos",
    "rank": "Puesto",
    "tier": "Tramo",
    "active_only": "Solo jugadores activos",
    "download_csv": "Descargar CSV",
    "close": "Cerrar",
    "no_results": "Sin resultados",
    "depth": "Puntos por tramo de puesto",
    "expand": "Gráfico y tabla",
    "difference": "Diferencia",
    "total": "Puntos totales",
    "methodology": "Cómo se recopilan los datos"
  },
  "pt": {
    "overview": "Visão geral",
    "members": "Membros",
    "opponent": "Adversário",
    "trends": "Tendências",
    "data": "Dados",
    "language": "Idioma",
    "skip": "Saltar para o conteúdo",
    "copy_link": "Copiar ligação",
    "copied": "Ligação copiada",
    "theme_light": "Mudar para modo dia",
    "theme_dark": "Mudar para modo noite",
    "points": "Pontos",
    "rank": "Posição",
    "tier": "Escalão",
    "active_only": "Apenas jogadores ativos",
    "download_csv": "Transferir CSV",
    "close": "Fechar",
    "no_results": "Sem resultados",
    "depth": "Pontos por escalão de posição",
    "expand": "Gráfico e tabela",
    "difference": "Diferença",
    "total": "Pontos totais",
    "methodology": "Como os dados são recolhidos"
  },
  "de": {
    "overview": "Übersicht",
    "members": "Mitglieder",
    "opponent": "Gegner",
    "trends": "Trends",
    "data": "Daten",
    "language": "Sprache",
    "skip": "Zum Inhalt springen",
    "copy_link": "Link kopieren",
    "copied": "Link kopiert",
    "theme_light": "Tagmodus",
    "theme_dark": "Nachtmodus",
    "points": "Punkte",
    "rank": "Rang",
    "tier": "Stufe",
    "active_only": "Nur aktive Spieler",
    "download_csv": "CSV herunterladen",
    "close": "Schließen",
    "no_results": "Keine Treffer",
    "depth": "Punkte nach Rangstufe",
    "expand": "Diagramm und Tabelle",
    "difference": "Differenz",
    "total": "Punkte gesamt",
    "methodology": "So werden die Daten erhoben"
  },
  "ko": {
    "overview": "개요",
    "members": "인원",
    "opponent": "상대",
    "trends": "추세",
    "data": "데이터",
    "language": "언어",
    "skip": "본문으로 건너뛰기",
    "copy_link": "링크 복사",
    "copied": "링크 복사됨",
    "theme_light": "주간 모드로 전환",
    "theme_dark": "야간 모드로 전환",
    "points": "포인트",
    "rank": "순위",
    "tier": "구간",
    "active_only": "활성 플레이어만",
    "download_csv": "CSV 다운로드",
    "close": "닫기",
    "no_results": "결과 없음",
    "depth": "순위 구간별 포인트",
    "expand": "차트와 표",
    "difference": "차이",
    "total": "총 포인트",
    "methodology": "데이터 수집 방법"
  },
  "zh": {
    "overview": "概览",
    "members": "成员",
    "opponent": "对手",
    "trends": "趋势",
    "data": "数据",
    "language": "语言",
    "skip": "跳到主要内容",
    "copy_link": "复制链接",
    "copied": "链接已复制",
    "theme_light": "切换到日间模式",
    "theme_dark": "切换到夜间模式",
    "points": "积分",
    "rank": "排名",
    "tier": "区间",
    "active_only": "仅显示活跃玩家",
    "download_csv": "下载 CSV",
    "close": "关闭",
    "no_results": "无匹配结果",
    "depth": "按排名区间的积分",
    "expand": "图表和表格",
    "difference": "差值",
    "total": "总积分",
    "methodology": "数据收集方式"
  }
}

# Columns: key | English | French | Russian | Turkish | Polish | Spanish |
# Portuguese | German | Korean | Simplified Chinese. No fallback strings.
TRANSLATIONS = r"""
leaderboards|Leaderboards|Classements|Рейтинги|Sıralamalar|Rankingi|Clasificaciones|Classificações|Ranglisten|순위표|排行榜
stages|Stages|Étapes|Этапы|Aşamalar|Etapy|Etapas|Etapas|Etappen|단계|阶段
week|Week|Semaine|Неделя|Hafta|Tydzień|Semana|Semana|Woche|주|周
search|Search players|Rechercher des joueurs|Поиск игроков|Oyuncu ara|Szukaj graczy|Buscar jugadores|Procurar jogadores|Spieler suchen|플레이어 검색|搜索玩家
loading|Loading…|Chargement…|Загрузка…|Yükleniyor…|Ładowanie…|Cargando…|A carregar…|Wird geladen…|불러오는 중…|加载中…
error|Could not load this week.|Impossible de charger cette semaine.|Не удалось загрузить эту неделю.|Bu hafta yüklenemedi.|Nie udało się wczytać tego tygodnia.|No se pudo cargar esta semana.|Não foi possível carregar esta semana.|Diese Woche konnte nicht geladen werden.|이번 주를 불러올 수 없습니다.|无法加载本周数据。
retry|Try again|Réessayer|Повторить|Tekrar dene|Spróbuj ponownie|Reintentar|Tentar novamente|Erneut versuchen|다시 시도|重试
final|Final|Définitif|Завершён|Tamamlandı|Zakończony|Finalizado|Final|Abgeschlossen|확정|已结束
live|Live|En cours|В процессе|Canlı|Na żywo|En curso|Em curso|Laufend|진행 중|实时
pending|Not started|Non commencé|Не начат|Başlamadı|Nie rozpoczęto|Sin empezar|Por iniciar|Noch nicht begonnen|시작 전|未开始
leading|Leading|En tête|Лидирует|Önde|Prowadzi|En cabeza|Na frente|In Führung|우세|领先
trailing|Trailing|Derrière|Отстаёт|Geride|Przegrywa|Por detrás|Atrás|Im Rückstand|열세|落后
clinched|{name} clinched|{name} a assuré la victoire|{name} обеспечил победу|{name} galibiyeti garantiledi|{name} zapewnia sobie zwycięstwo|{name} aseguró la victoria|{name} garantiu a vitória|{name} hat den Sieg gesichert|{name} 승리 확정|{name} 已锁定胜利
in_progress|In progress|En cours|В процессе|Devam ediyor|W toku|En curso|Em curso|Läuft|진행 중|进行中
captured|Captured {date}|Capturé le {date}|Снято {date}|Kayıt: {date}|Zapisano {date}|Capturado el {date}|Capturado em {date}|Erfasst am {date}|캡처: {date}|采集于 {date}
weekly_points|Weekly points|Points hebdomadaires|Очки за неделю|Haftalık puan|Punkty tygodniowe|Puntos semanales|Pontos semanais|Wochenpunkte|주간 포인트|周积分
share|Share|Part|Доля|Pay|Udział|Proporción|Quota|Anteil|비중|占比
quota|Quota|Objectif|Норма|Hedef|Cel|Objetivo|Meta|Soll|목표|配额
met|Met|Atteint|Выполнена|Ulaşıldı|Osiągnięty|Alcanzado|Atingida|Erfüllt|달성|已达标
near|Near|Proche|Близко|Yakın|Blisko|Cerca|Perto|Fast erreicht|근접|接近
below|Below|En dessous|Ниже нормы|Altında|Poniżej|Por debajo|Abaixo|Darunter|미달|未达标
deficit|Deficit|Manque|Нехватка|Eksik|Brak|Déficit|Défice|Fehlbetrag|부족분|差额
players|Players|Joueurs|Игроки|Oyuncular|Gracze|Jugadores|Jogadores|Spieler|플레이어|玩家
player|Player|Joueur|Игрок|Oyuncu|Gracz|Jugador|Jogador|Spieler|플레이어|玩家
active_days|Active days|Jours actifs|Активные дни|Aktif günler|Aktywne dni|Días activos|Dias ativos|Aktive Tage|활동 일수|活跃天数
consistency|Consistency|Régularité|Стабильность|İstikrar|Regularność|Regularidad|Regularidade|Beständigkeit|꾸준함|稳定性
checksum|Checksum|Vérification des totaux|Проверка суммы|Toplam kontrolü|Kontrola sumy|Comprobación de sumas|Verificação de somas|Summenprüfung|합계 검증|合计校验
exact|Exact|Conforme|Совпадает|Tam eşleşme|Zgodna|Exacto|Exato|Exakt|일치|一致
alliance_change|Alliance change|Changement d'alliance|Смена альянса|İttifak değişikliği|Zmiana sojuszu|Cambio de alianza|Mudança de aliança|Allianzwechsel|연맹 변경|联盟变更
mismatch|Mismatch|Écart|Расхождение|Uyuşmazlık|Rozbieżność|Discrepancia|Divergência|Abweichung|불일치|不一致
all|All|Tous|Все|Tümü|Wszyscy|Todos|Todos|Alle|전체|全部
filter|Filter|Filtrer|Фильтр|Filtre|Filtruj|Filtrar|Filtrar|Filtern|필터|筛选
sort|Sort|Trier|Сортировка|Sırala|Sortuj|Ordenar|Ordenar|Sortieren|정렬|排序
days|Days|Jours|Дни|Günler|Dni|Días|Dias|Tage|일수|天数
mon|Mon|Lun|Пн|Pzt|Pon|Lun|Seg|Mo|월|周一
tue|Tue|Mar|Вт|Sal|Wt|Mar|Ter|Di|화|周二
wed|Wed|Mer|Ср|Çar|Śr|Mié|Qua|Mi|수|周三
thu|Thu|Jeu|Чт|Per|Czw|Jue|Qui|Do|목|周四
fri|Fri|Ven|Пт|Cum|Pt|Vie|Sex|Fr|금|周五
sat|Sat|Sam|Сб|Cmt|Sob|Sáb|Sáb|Sa|토|周六
week_board|This Week|Cette semaine|Эта неделя|Bu hafta|Ten tydzień|Esta semana|Esta semana|Diese Woche|이번 주|本周
download_json|Download JSON|Télécharger le JSON|Скачать JSON|JSON indir|Pobierz JSON|Descargar JSON|Transferir JSON|JSON herunterladen|JSON 다운로드|下载 JSON
live_note|Live snapshot: points and ranks may change.|Instantané en cours : les points et les rangs peuvent changer.|Текущий снимок: очки и места могут измениться.|Canlı kayıt: puanlar ve sıralamalar değişebilir.|Migawka na żywo: punkty i miejsca mogą się zmienić.|Captura en curso: los puntos y puestos pueden cambiar.|Captura em curso: os pontos e as posições podem mudar.|Laufende Momentaufnahme: Punkte und Ränge können sich ändern.|진행 중인 기록입니다. 포인트와 순위가 바뀔 수 있습니다.|实时快照：积分与排名可能变化。
stage_points|Points per stage|Points par étape|Очки по этапам|Aşama başına puan|Punkty na etap|Puntos por etapa|Pontos por etapa|Punkte je Etappe|단계별 포인트|各阶段积分
rest|Rest|Reste|Остальные|Diğerleri|Pozostali|Resto|Restantes|Übrige|나머지|其余
head_to_head|Head-to-head by rank|Duel par rang|Сравнение по месту|Sıraya göre karşılaştırma|Porównanie według miejsca|Cara a cara por puesto|Frente a frente por posição|Direktvergleich nach Rang|순위별 맞대결|同排名对比
top_performers|Top performers|Meilleurs joueurs|Лучшие игроки|En iyi oyuncular|Najlepsi gracze|Mejores jugadores|Melhores jogadores|Beste Spieler|최고 성적 플레이어|最佳玩家
record|Record|Bilan|Результат|Galibiyet–mağlubiyet|Bilans|Balance|Balanço|Bilanz|전적|战绩
stage_win_rate|Stage win rate|Taux de victoire par étape|Доля побед по этапам|Aşama kazanma oranı|Odsetek wygranych etapów|Porcentaje de victorias por etapa|Taxa de vitórias por etapa|Siegquote je Etappe|단계별 승률|各阶段胜率
career|Member career|Parcours des membres|История участников|Üye geçmişi|Historia członków|Trayectoria de miembros|Percurso dos membros|Mitgliederverlauf|멤버 누적 기록|成员历程
weeks_played|Weeks played|Semaines jouées|Недель сыграно|Katıldığı haftalar|Rozegrane tygodnie|Semanas jugadas|Semanas jogadas|Gespielte Wochen|참가 주 수|参赛周数
average|Average|Moyenne|Среднее|Ortalama|Średnia|Promedio|Média|Durchschnitt|평균|平均
best|Best|Meilleur|Лучший|En iyi|Najlepszy|Mejor|Melhor|Beste|최고|最佳
last_week|Last week|Dernière semaine|Последняя неделя|Son hafta|Ostatni tydzień|Última semana|Última semana|Letzte Woche|마지막 주|最近一周
trend|Trend|Tendance|Динамика|Eğilim|Trend|Tendencia|Tendência|Entwicklung|추세|趋势
need_two|Trends need at least two recorded weeks.|Les tendances nécessitent au moins deux semaines enregistrées.|Для динамики нужны хотя бы две записанные недели.|Eğilimler için en az iki haftalık kayıt gerekir.|Trendy wymagają co najmniej dwóch zapisanych tygodni.|Las tendencias requieren al menos dos semanas registradas.|As tendências precisam de pelo menos duas semanas registadas.|Trends erfordern mindestens zwei erfasste Wochen.|추세를 보려면 최소 두 주의 기록이 필요합니다.|至少记录两周后才可显示趋势。
history|Weekly history|Historique hebdomadaire|История по неделям|Haftalık geçmiş|Historia tygodniowa|Historial semanal|Histórico semanal|Wochenverlauf|주간 기록|每周历史
best_week|Best week|Meilleure semaine|Лучшая неделя|En iyi hafta|Najlepszy tydzień|Mejor semana|Melhor semana|Beste Woche|최고 기록 주|最佳周
daily_ranks|Daily ranks|Rangs quotidiens|Места по дням|Günlük sıralamalar|Dzienne miejsca|Puestos diarios|Posições diárias|Tagesränge|일별 순위|每日排名
overall_rank|Overall rank|Rang général|Общее место|Genel sıra|Miejsce ogólne|Puesto general|Posição geral|Gesamtrang|전체 순위|总排名
alliance_rank|Alliance rank|Rang dans l'alliance|Место в альянсе|İttifak sırası|Miejsce w sojuszu|Puesto en la alianza|Posição na aliança|Allianzrang|연맹 내 순위|联盟内排名
integrity|Data integrity|Intégrité des données|Целостность данных|Veri bütünlüğü|Integralność danych|Integridad de datos|Integridade dos dados|Datenintegrität|데이터 무결성|数据完整性
rows|Rows|Lignes|Строки|Satırlar|Wiersze|Filas|Linhas|Zeilen|행 수|行数
contiguous|Contiguous ranks|Rangs consécutifs|Без пропусков мест|Kesintisiz sıralar|Ciągłość miejsc|Puestos consecutivos|Posições consecutivas|Lückenlose Ränge|연속 순위|排名连续
descending|Points descending|Points décroissants|Очки по убыванию|Azalan puanlar|Punkty malejąco|Puntos descendentes|Pontos decrescentes|Punkte absteigend|포인트 내림차순|积分降序
unresolved|Unresolved|Non résolu|Не разрешено|Çözümlenmemiş|Nierozstrzygnięte|Sin resolver|Por resolver|Ungeklärt|미해결|未解决
yes|Yes|Oui|Да|Evet|Tak|Sí|Sim|Ja|예|是
no|No|Non|Нет|Hayır|Nie|No|Não|Nein|아니요|否
screenshots|Capture screenshots|Captures d'écran|Снимки экрана|Ekran görüntüleri|Zrzuty ekranu|Capturas de pantalla|Capturas de ecrã|Bildschirmaufnahmen|캡처 화면|采集截图
methodology_text|Captured from the game client using on-device text recognition. Every rank is read at least twice and voted; gaps are re-read. Live tabs are scanned twice and merged.|Capturé depuis le client du jeu par reconnaissance de texte sur l'appareil. Chaque rang est lu au moins deux fois et retenu par vote ; les lacunes sont relues. Les onglets en cours sont parcourus deux fois puis fusionnés.|Данные снимаются с игрового клиента и распознаются на устройстве. Каждое место читается не менее двух раз и выбирается голосованием; пропуски читаются повторно. Текущие вкладки сканируются дважды и объединяются.|Oyun istemcisinden cihaz üzerinde metin tanımayla kaydedilir. Her sıra en az iki kez okunup oylamayla belirlenir; boşluklar yeniden okunur. Canlı sekmeler iki kez taranıp birleştirilir.|Dane są zapisywane z klienta gry i odczytywane przez rozpoznawanie tekstu na urządzeniu. Każde miejsce jest odczytywane co najmniej dwukrotnie i wybierane głosowaniem; luki są odczytywane ponownie. Karty na żywo są skanowane dwukrotnie i scalane.|Se captura desde el cliente del juego mediante reconocimiento de texto en el dispositivo. Cada puesto se lee al menos dos veces y se decide por votación; los huecos se releen. Las pestañas en curso se escanean dos veces y se combinan.|Capturado do cliente do jogo com reconhecimento de texto no dispositivo. Cada posição é lida pelo menos duas vezes e escolhida por votação; as lacunas são relidas. Os separadores em curso são lidos duas vezes e combinados.|Aus dem Spielclient mit Texterkennung auf dem Gerät erfasst. Jeder Rang wird mindestens zweimal gelesen und per Abstimmung gewählt; Lücken werden erneut gelesen. Laufende Reiter werden zweimal erfasst und zusammengeführt.|게임 클라이언트 화면을 기기 내 문자 인식으로 읽습니다. 모든 순위를 최소 두 번 읽고 다수결로 결정하며, 누락 부분은 다시 읽습니다. 진행 중인 탭은 두 번 스캔하여 병합합니다.|从游戏客户端采集，并使用设备端文字识别。每个名次至少读取两次并通过投票确定；缺漏处重新读取。实时标签页扫描两次后合并。
server_time|Server time (UTC−2)|Heure serveur (UTC−2)|Время сервера (UTC−2)|Sunucu saati (UTC−2)|Czas serwera (UTC−2)|Hora del servidor (UTC−2)|Hora do servidor (UTC−2)|Serverzeit (UTC−2)|서버 시간 (UTC−2)|服务器时间（UTC−2）
rules|Rules|Règles|Правила|Kurallar|Zasady|Reglas|Regras|Regeln|규칙|规则
rules_text|Monday awards 1 win, Tuesday–Friday 2 each, and Saturday 4: 13 total. Seven wins clinch the match. Only final stages count toward the score.|Le lundi rapporte 1 victoire, du mardi au vendredi 2 chacune, et le samedi 4 : 13 au total. Sept victoires assurent le match. Seules les étapes terminées comptent dans le score.|Понедельник даёт 1 победу, вторник–пятница по 2, суббота 4: всего 13. Семь побед гарантируют выигрыш матча. В счёт входят только завершённые этапы.|Pazartesi 1, salı–cuma günde 2, cumartesi 4 galibiyet verir: toplam 13. Yedi galibiyet maçı kazanmayı garantiler. Skora yalnızca tamamlanan aşamalar sayılır.|Poniedziałek daje 1 wygraną, wtorek–piątek po 2, a sobota 4: łącznie 13. Siedem wygranych zapewnia zwycięstwo w meczu. Do wyniku liczą się tylko zakończone etapy.|El lunes otorga 1 victoria, de martes a viernes 2 cada día y el sábado 4: 13 en total. Siete victorias aseguran el duelo. Solo las etapas finalizadas cuentan en el marcador.|Segunda-feira dá 1 vitória, terça a sexta 2 por dia e sábado 4: 13 no total. Sete vitórias garantem o duelo. Só as etapas concluídas contam para o resultado.|Montag zählt 1 Sieg, Dienstag–Freitag je 2 und Samstag 4: insgesamt 13. Sieben Siege sichern den Gesamtsieg. Nur abgeschlossene Etappen zählen zum Spielstand.|월요일은 1승, 화요일~금요일은 하루 2승, 토요일은 4승으로 총 13승입니다. 7승을 확보하면 승리가 확정됩니다. 완료된 단계만 점수에 반영됩니다.|周一计1胜，周二至周五每天计2胜，周六计4胜，共13胜。获得7胜即可锁定胜利。比分仅计入已结束的阶段。
footer|Z Route: Redemption · Server 117 · VS intelligence · maintained by JeffxLabs|Z Route: Redemption · Serveur 117 · Renseignement VS · maintenu par JeffxLabs|Z Route: Redemption · Сервер 117 · Аналитика VS · поддерживает JeffxLabs|Z Route: Redemption · Sunucu 117 · VS analizleri · JeffxLabs tarafından hazırlanır|Z Route: Redemption · Serwer 117 · Analiza VS · prowadzi JeffxLabs|Z Route: Redemption · Servidor 117 · Análisis VS · mantenido por JeffxLabs|Z Route: Redemption · Servidor 117 · Análise VS · mantido por JeffxLabs|Z Route: Redemption · Server 117 · VS-Analyse · betreut von JeffxLabs|Z Route: Redemption · 서버 117 · VS 분석 · 운영: JeffxLabs|Z Route: Redemption · 服务器117 · VS情报 · 由JeffxLabs维护
titan|Titan|Titan|Титан|Dev|Tytan|Titán|Titã|Titan|거인|巨擘
high|High scorer|Gros contributeur|Высокий вклад|Yüksek puanlı|Wysoki wynik|Gran contribuidor|Grande contribuidor|Hohe Punktzahl|고득점|高分
core|Core|Noyau|Основа|Çekirdek|Trzon|Núcleo|Núcleo|Kern|핵심|核心
quota_met|Quota met|Objectif atteint|Норма выполнена|Hedefe ulaştı|Cel osiągnięty|Objetivo alcanzado|Meta atingida|Soll erfüllt|목표 달성|配额达标
near_quota|Near quota|Proche de l'objectif|Близко к норме|Hedefe yakın|Blisko celu|Cerca del objetivo|Perto da meta|Nahe am Soll|목표 근접|接近配额
passenger|Passenger|Passager|Пассажир|Yolcu|Pasażer|Pasajero|Passageiro|Mitläufer|저참여|低贡献
check_exact|Daily sum matches weekly points.|La somme des jours correspond aux points hebdomadaires.|Сумма дней совпадает с очками за неделю.|Günlük toplam haftalık puanla eşleşiyor.|Suma dni zgadza się z punktami tygodniowymi.|La suma diaria coincide con los puntos semanales.|A soma diária corresponde aos pontos semanais.|Die Tagessumme entspricht den Wochenpunkten.|일별 합계와 주간 포인트가 일치합니다.|每日合计与周积分一致。
check_live|Points kept rising between the day and weekly scans (the board was still updating before the reset).|Les points ont encore augmenté entre la lecture du jour et celle de la semaine (classement encore actif avant la réinitialisation).|Очки выросли между снимками дня и недели (таблица ещё обновлялась до сброса).|Puanlar günlük ve haftalık tarama arasında arttı (tablo sıfırlamadan önce hâlâ güncelleniyordu).|Punkty wzrosły między odczytem dnia i tygodnia (tabela jeszcze się aktualizowała przed resetem).|Los puntos siguieron subiendo entre la lectura del día y la semanal (la tabla aún se actualizaba antes del reinicio).|Os pontos continuaram a subir entre a leitura do dia e a semanal (a tabela ainda atualizava antes do reinício).|Die Punkte stiegen zwischen Tages- und Wochenscan weiter (die Liste lief vor dem Reset noch).|일별 스캔과 주간 스캔 사이에 포인트가 늘었습니다(초기화 전 순위표가 아직 갱신 중).|在当日与本周扫描之间积分仍在增加（重置前榜单仍在更新）。
check_alliance_change|Alliance membership changed during this week.|L'appartenance à l'alliance a changé durant cette semaine.|Принадлежность к альянсу изменилась на этой неделе.|Bu hafta ittifak üyeliği değişti.|Przynależność do sojuszu zmieniła się w tym tygodniu.|La pertenencia a la alianza cambió durante esta semana.|A pertença à aliança mudou durante esta semana.|Die Allianzzugehörigkeit hat sich in dieser Woche geändert.|이번 주에 소속 연맹이 변경되었습니다.|本周内联盟归属发生变化。
check_mismatch|Daily sum differs from weekly points; review capture data.|La somme des jours diffère des points hebdomadaires ; vérifier les captures.|Сумма дней отличается от очков за неделю; проверьте снимки.|Günlük toplam haftalık puandan farklı; kayıt verilerini inceleyin.|Suma dni różni się od punktów tygodniowych; sprawdź dane zrzutów.|La suma diaria difiere de los puntos semanales; revise las capturas.|A soma diária difere dos pontos semanais; consulte as capturas.|Die Tagessumme weicht von den Wochenpunkten ab; Aufnahmen prüfen.|일별 합계와 주간 포인트가 다릅니다. 캡처 데이터를 확인하세요.|每日合计与周积分不符，请查看采集数据。
match|Match|Duel|Матч|Maç|Mecz|Duelo|Duelo|Duell|대결|对决
score|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}|{home} : {opp} / {total}
wins_remaining|{n} wins remaining|{n} victoires restantes|Осталось побед: {n}|Kalan galibiyet: {n}|Pozostałe wygrane: {n}|Quedan {n} victorias|Restam {n} vitórias|{n} Siege verbleiben|남은 승수: {n}|剩余 {n} 胜
top10|Top 10|10 premiers|Топ-10|İlk 10|Najlepsza 10|Primeros 10|Primeiros 10|Beste 10|상위 10명|前10名
top20|Ranks 11–20|Rangs 11–20|Места 11–20|11–20. sıralar|Miejsca 11–20|Puestos 11–20|Posições 11–20|Ränge 11–20|11~20위|第11至20名
top50|Ranks 21–50|Rangs 21–50|Места 21–50|21–50. sıralar|Miejsca 21–50|Puestos 21–50|Posições 21–50|Ränge 21–50|21~50위|第21至50名
top100|Ranks 51–100|Rangs 51–100|Места 51–100|51–100. sıralar|Miejsca 51–100|Puestos 51–100|Posições 51–100|Ränge 51–100|51~100위|第51至100名
wins_one|{n} win|{n} victoire|{n} победа|{n} galibiyet|{n} wygrana|{n} victoria|{n} vitória|{n} Sieg|{n}승|{n}胜
wins_other|{n} wins|{n} victoires|{n} победы|{n} galibiyet|{n} wygranej|{n} victorias|{n} vitórias|{n} Siege|{n}승|{n}胜
wins_few|{n} wins|{n} victoires|{n} победы|{n} galibiyet|{n} wygrane|{n} victorias|{n} vitórias|{n} Siege|{n}승|{n}胜
wins_many|{n} wins|{n} victoires|{n} побед|{n} galibiyet|{n} wygranych|{n} victorias|{n} vitórias|{n} Siege|{n}승|{n}胜
joined|Joined|A rejoint|Присоединился|Katıldı|Dołączył|Se incorporó|Entrou|Beigetreten|가입|已加入
left|Left|A quitté|Покинул|Ayrıldı|Odszedł|Se fue|Saiu|Ausgetreten|탈퇴|已离开
include_left|Include players who left|Inclure les joueurs partis|Включить ушедших игроков|Ayrılan oyuncuları dahil et|Uwzględnij graczy, którzy odeszli|Incluir jugadores que se fueron|Incluir jogadores que saíram|Ausgetretene Spieler einbeziehen|탈퇴한 플레이어 포함|包括已离开的玩家
check_joined|First appeared on a daily board after Monday; points earned before joining appear only in the weekly total.|Première apparition sur un classement quotidien après lundi ; les points gagnés avant de rejoindre figurent uniquement dans le total hebdomadaire.|Впервые появился в дневном рейтинге после понедельника; очки до вступления учтены только в недельном итоге.|Pazartesiden sonra ilk kez günlük sıralamada göründü; katılmadan önce kazanılan puanlar yalnızca haftalık toplamda yer alır.|Po raz pierwszy pojawił się w rankingu dziennym po poniedziałku; punkty zdobyte przed dołączeniem są tylko w sumie tygodniowej.|Apareció por primera vez en una clasificación diaria después del lunes; los puntos anteriores a su incorporación solo figuran en el total semanal.|Apareceu pela primeira vez numa classificação diária após segunda-feira; os pontos anteriores à entrada constam apenas do total semanal.|Erschien erstmals nach Montag auf einer Tagesrangliste; Punkte vor dem Beitritt sind nur in der Wochensumme enthalten.|월요일 이후 일일 순위표에 처음 등장했습니다. 가입 전 획득한 포인트는 주간 합계에만 포함됩니다.|周一后首次出现在每日榜单上；加入前获得的积分仅计入周合计。
check_left|Appears on daily boards but is no longer on the weekly board; excluded from weekly ranks.|Figure sur des classements quotidiens mais plus sur le classement hebdomadaire ; exclu des rangs hebdomadaires.|Есть в дневных рейтингах, но больше нет в недельном; не участвует в недельном ранжировании.|Günlük sıralamalarda var ancak artık haftalık sıralamada yok; haftalık derecelendirmeye dahil edilmez.|Jest w rankingach dziennych, ale nie ma go już w tygodniowym; nie otrzymuje pozycji tygodniowej.|Figura en clasificaciones diarias, pero ya no en la semanal; no recibe puesto semanal.|Consta de classificações diárias, mas já não da semanal; não recebe posição semanal.|Auf Tagesranglisten, aber nicht mehr auf der Wochenrangliste; ohne Wochenplatzierung.|일일 순위표에는 있지만 주간 순위표에는 더 이상 없습니다. 주간 순위에서 제외됩니다.|出现在每日榜单上，但已不在周榜单中；不参与周排名。
win|Win|Victoire|Победа|Galibiyet|Wygrana|Victoria|Vitória|Sieg|승|胜
loss|Loss|Défaite|Поражение|Mağlubiyet|Przegrana|Derrota|Derrota|Niederlage|패|负
undecided|Undecided|Non décidé|Не решён|Sonuçlanmadı|Nierozstrzygnięty|Sin decidir|Por decidir|Offen|미확정|未决
not_on_weekly|Not on weekly board|Absent du classement hebdomadaire|Нет в недельном рейтинге|Haftalık sıralamada yok|Brak w rankingu tygodniowym|No figura en la tabla semanal|Ausente da tabela semanal|Nicht in der Wochenrangliste|주간 순위표에 없음|未上周榜
copy_manual|Copy this link|Copier ce lien|Скопируйте эту ссылку|Bu bağlantıyı kopyala|Skopiuj ten link|Copiar este enlace|Copiar esta ligação|Diesen Link kopieren|이 링크 복사|复制此链接
quota_target|Weekly target: {n}|Objectif hebdomadaire : {n}|Норма за неделю: {n}|Haftalık hedef: {n}|Cel tygodniowy: {n}|Objetivo semanal: {n}|Meta semanal: {n}|Wochenziel: {n}|주간 목표: {n}|周目标：{n}
capture_note|Only completed stages count toward the match score; live leads are provisional.|Seules les étapes terminées comptent dans le score ; les avances en cours sont provisoires.|В счёт входят только завершённые этапы; текущее лидерство предварительное.|Maç skoruna yalnızca tamamlanan aşamalar sayılır; canlı liderlik geçicidir.|Do wyniku meczu liczą się tylko zakończone etapy; prowadzenie na żywo jest tymczasowe.|Solo las etapas completadas cuentan en el marcador; las ventajas en curso son provisionales.|Só as etapas concluídas contam para o resultado; as vantagens em curso são provisórias.|Nur abgeschlossene Etappen zählen zum Spielstand; laufende Führungen sind vorläufig.|완료된 단계만 대결 점수에 반영하며 진행 중인 우세는 잠정적입니다.|比分仅计入已结束阶段，实时领先结果尚未确定。
stage_1|Radar Exploration|Exploration radar|Радарная разведка|Radar keşfi|Eksploracja radarowa|Exploración de radar|Exploração de radar|Radarerkundung|레이더 탐색|雷达探索
stage_2|Base Construction|Construction de base|Строительство базы|Üs inşası|Budowa bazy|Construcción de base|Construção da base|Basisausbau|기지 건설|基地建设
stage_3|Tech Research|Recherche technologique|Исследование технологий|Teknoloji araştırması|Badania technologiczne|Investigación tecnológica|Investigação tecnológica|Technologieforschung|기술 연구|科技研究
stage_4|Hero Training|Entraînement des héros|Подготовка героев|Kahraman eğitimi|Szkolenie bohaterów|Entrenamiento de héroes|Treino de heróis|Heldentraining|영웅 훈련|英雄训练
stage_5|Full Military Preparation|Préparation militaire complète|Полная военная подготовка|Tam askerî hazırlık|Pełne przygotowanie wojskowe|Preparación militar completa|Preparação militar completa|Umfassende Militärvorbereitung|전면 군사 준비|全面军事准备
stage_6|Enemy Assault|Assaut ennemi|Штурм противника|Düşmana saldırı|Szturm na wroga|Asalto al enemigo|Assalto ao inimigo|Feindangriff|적 공격|突袭敌军
stage_desc_1|Exploration, radar tasks, fighter development, stamina use and resource gathering.|Exploration, missions radar, développement des chasseurs, dépense d'endurance et collecte de ressources.|Разведка, задания радара, развитие истребителя, расход выносливости и сбор ресурсов.|Keşif, radar görevleri, savaşçı geliştirme, dayanıklılık kullanımı ve kaynak toplama.|Eksploracja, zadania radarowe, rozwój myśliwca, zużycie wytrzymałości i zbieranie zasobów.|Exploración, misiones de radar, desarrollo del caza, uso de energía y recolección de recursos.|Exploração, tarefas de radar, desenvolvimento do caça, uso de resistência e recolha de recursos.|Erkundung, Radaraufgaben, Jägerentwicklung, Ausdauerverbrauch und Ressourcensammlung.|탐색, 레이더 임무, 전투기 개발, 스태미나 사용 및 자원 채집.|探索、雷达任务、战斗机发展、体力消耗和资源采集。
stage_desc_2|Base expansion, construction power, building speedups, survivor recruitment and UR logistics.|Extension de base, puissance de construction, accélérations de construction, recrutement de survivants et logistique UR.|Расширение базы, сила строительства, ускорения строительства, набор выживших и логистика UR.|Üs genişletme, inşaat gücü, inşaat hızlandırmaları, hayatta kalan alımı ve UR lojistiği.|Rozbudowa bazy, moc budowy, przyspieszenia budowy, rekrutacja ocalałych i logistyka UR.|Ampliación de base, poder de construcción, aceleraciones de construcción, reclutamiento de supervivientes y logística UR.|Expansão da base, poder de construção, acelerações de construção, recrutamento de sobreviventes e logística UR.|Basisausbau, Baumacht, Baubeschleunigungen, Überlebendenrekrutierung und UR-Logistik.|기지 확장, 건설 전투력, 건설 가속, 생존자 모집 및 UR 물류.|基地扩建、建设战力、建造加速、幸存者招募及UR物流。
stage_desc_3|Technology, research speedups, research power and fighter component chests.|Technologie, accélérations de recherche, puissance de recherche et coffres de composants de chasseurs.|Технологии, ускорения исследований, сила исследований и сундуки компонентов истребителя.|Teknoloji, araştırma hızlandırmaları, araştırma gücü ve savaşçı bileşen sandıkları.|Technologia, przyspieszenia badań, moc badań i skrzynie komponentów myśliwca.|Tecnología, aceleraciones de investigación, poder de investigación y cofres de componentes del caza.|Tecnologia, acelerações de investigação, poder de investigação e baús de componentes do caça.|Technologie, Forschungsbeschleunigungen, Forschungsmacht und Jägerkomponententruhen.|기술, 연구 가속, 연구 전투력 및 전투기 부품 상자.|科技、研究加速、研究战力及战斗机组件宝箱。
stage_desc_4|Hero development and recruitment, skill EXP books, hero EXP and UR/SSR/SR hero shards.|Développement et recrutement des héros, livres d'EXP de compétence, EXP de héros et fragments de héros UR/SSR/SR.|Развитие и набор героев, книги опыта навыков, опыт героев и фрагменты героев UR/SSR/SR.|Kahraman geliştirme ve alımı, beceri deneyim kitapları, kahraman deneyimi ve UR/SSR/SR kahraman parçaları.|Rozwój i rekrutacja bohaterów, księgi doświadczenia umiejętności, doświadczenie bohaterów i fragmenty bohaterów UR/SSR/SR.|Desarrollo y reclutamiento de héroes, libros de experiencia de habilidades, experiencia de héroes y fragmentos de héroes UR/SSR/SR.|Desenvolvimento e recrutamento de heróis, livros de experiência de habilidades, experiência de heróis e fragmentos de heróis UR/SSR/SR.|Heldenentwicklung und -rekrutierung, Fertigkeits-EP-Bücher, Helden-EP und UR/SSR/SR-Heldensplitter.|영웅 성장과 모집, 스킬 경험치 책, 영웅 경험치 및 UR/SSR/SR 영웅 조각.|英雄培养与招募、技能经验书、英雄经验及UR/SSR/SR英雄碎片。
stage_desc_5|Train T1–T10 troops; use training, building and research speedups; gain construction and research power.|Entraîner des troupes T1–T10 ; utiliser des accélérations d'entraînement, de construction et de recherche ; gagner de la puissance de construction et de recherche.|Подготовка войск T1–T10; ускорения подготовки, строительства и исследований; рост силы строительства и исследований.|T1–T10 asker eğitimi; eğitim, inşaat ve araştırma hızlandırmaları; inşaat ve araştırma gücü kazanımı.|Szkolenie oddziałów T1–T10; przyspieszenia szkolenia, budowy i badań; wzrost mocy budowy i badań.|Entrenar tropas T1–T10; usar aceleraciones de entrenamiento, construcción e investigación; aumentar el poder de construcción e investigación.|Treinar tropas T1–T10; usar acelerações de treino, construção e investigação; ganhar poder de construção e investigação.|T1–T10-Truppen ausbilden; Ausbildungs-, Bau- und Forschungsbeschleunigungen nutzen; Bau- und Forschungsmacht steigern.|T1~T10 병사 훈련, 훈련·건설·연구 가속 사용 및 건설·연구 전투력 증가.|训练T1至T10部队，使用训练、建造与研究加速，提升建设与研究战力。
stage_desc_6|Cross-server raids, enemy eliminations and troop losses (T1–T10), healing speedups, UR missions and logistics.|Raids inter-serveurs, éliminations ennemies et pertes de troupes (T1–T10), accélérations de soins, missions UR et logistique.|Межсерверные рейды, уничтожение врагов и потери войск T1–T10, ускорения лечения, задания UR и логистика.|Sunucular arası baskınlar, düşman öldürme ve asker kayıpları (T1–T10), iyileştirme hızlandırmaları, UR görevleri ve lojistik.|Najazdy między serwerami, eliminacja wrogów i straty oddziałów (T1–T10), przyspieszenia leczenia, misje UR i logistyka.|Incursiones entre servidores, bajas enemigas y propias (T1–T10), aceleraciones de curación, misiones UR y logística.|Incursões entre servidores, eliminações inimigas e perdas de tropas (T1–T10), acelerações de cura, missões UR e logística.|Serverübergreifende Raids, besiegte Feinde und Truppenverluste (T1–T10), Heilungsbeschleunigungen, UR-Missionen und Logistik.|서버 간 습격, 적 처치와 병사 손실(T1~T10), 치료 가속, UR 임무 및 물류.|跨服突袭、击败敌兵与士兵损失（T1至T10）、治疗加速、UR任务及物流。
alliance|Alliance|Alliance|Альянс|İttifak|Sojusz|Alianza|Aliança|Allianz|연맹|联盟
score_label|Match score|Score du duel|Счёт матча|Maç skoru|Wynik meczu|Marcador del duelo|Resultado do duelo|Spielstand|대결 점수|对决比分
consistency_hint|Coefficient of variation; lower is steadier.|Coefficient de variation ; plus il est bas, plus le joueur est régulier.|Коэффициент вариации: чем ниже, тем стабильнее.|Değişim katsayısı; düşük değer daha istikrarlıdır.|Współczynnik zmienności; niższy oznacza większą regularność.|Coeficiente de variación; cuanto menor, más regular.|Coeficiente de variação; quanto menor, mais regular.|Variationskoeffizient; niedriger bedeutet beständiger.|변동계수입니다. 낮을수록 더 꾸준합니다.|变异系数；越低越稳定。
checksum_hint|Weekly points compared with the sum of daily points.|Points hebdomadaires comparés à la somme des points quotidiens.|Очки за неделю в сравнении с суммой очков по дням.|Haftalık puanların günlük puan toplamıyla karşılaştırması.|Punkty tygodniowe porównane z sumą punktów dziennych.|Puntos semanales comparados con la suma de puntos diarios.|Pontos semanais comparados com a soma dos pontos diários.|Wochenpunkte im Vergleich zur Summe der Tagespunkte.|주간 포인트와 일별 포인트 합계를 비교합니다.|周积分与每日积分合计的比较。
missing_points|Missing points|Points manquants|Отсутствующие очки|Eksik puanlar|Brakujące punkty|Puntos ausentes|Pontos em falta|Fehlende Punkte|누락된 포인트|缺失积分
missing_names|Missing names|Noms manquants|Отсутствующие имена|Eksik adlar|Brakujące nazwy|Nombres ausentes|Nomes em falta|Fehlende Namen|누락된 이름|缺失名称
profile_absent|Not on the roster in the selected week; showing {date}.|Absent de l'effectif de la semaine sélectionnée ; affichage du {date}.|Нет в составе выбранной недели; показаны данные за {date}.|Seçilen haftanın kadrosunda yok; {date} gösteriliyor.|Nieobecny w składzie wybranego tygodnia; pokazano {date}.|No está en la plantilla de la semana seleccionada; se muestra {date}.|Ausente do plantel da semana selecionada; a mostrar {date}.|Nicht im Kader der gewählten Woche; angezeigt wird {date}.|선택한 주의 명단에 없습니다. {date} 기록을 표시합니다.|未在所选周的名单中；显示 {date} 的记录。
days_total|Daily total|Total des jours|Сумма по дням|Günlük toplam|Suma dni|Total diario|Total diário|Tagessumme|일별 합계|每日合计
depth_note|Players are ranked within each alliance; difference is home minus opponent.|Les joueurs sont classés au sein de chaque alliance ; l'écart est notre alliance moins l'adversaire.|Игроки ранжируются внутри каждого альянса; разница — наш альянс минус противник.|Oyuncular kendi ittifaklarında sıralanır; fark kendi ittifakımız eksi rakiptir.|Gracze są klasyfikowani w obrębie każdego sojuszu; różnica to nasz sojusz minus przeciwnik.|Los jugadores se clasifican dentro de cada alianza; la diferencia es nuestra alianza menos el rival.|Os jogadores são classificados dentro de cada aliança; a diferença é a nossa aliança menos o adversário.|Spieler werden innerhalb jeder Allianz gereiht; Differenz ist unsere Allianz minus Gegner.|각 연맹 내 순위로 비교합니다. 차이는 우리 연맹에서 상대를 뺀 값입니다.|玩家按各自联盟内排名比较；差值为我方减去对手。
live_history_note|Live weekly totals are provisional.|Les totaux hebdomadaires en cours sont provisoires.|Текущие недельные итоги предварительные.|Canlı haftalık toplamlar geçicidir.|Tygodniowe sumy na żywo są tymczasowe.|Los totales semanales en curso son provisionales.|Os totais semanais em curso são provisórios.|Laufende Wochensummen sind vorläufig.|진행 중인 주간 합계는 잠정적입니다.|实时周合计尚未确定。
snapshot|Snapshot|Instantané|Снимок|Kayıt|Migawka|Captura|Captura|Momentaufnahme|스냅샷|快照
snapshots|Snapshots|Instantanés|Снимки|Kayıtlar|Migawki|Capturas|Capturas|Momentaufnahmen|스냅샷|快照
source|Source|Source|Источник|Kaynak|Źródło|Fuente|Fonte|Quelle|출처|来源
approximate|approximate|approximatif|приблизительно|yaklaşık|przybliżony|aproximado|aproximado|ungefähr|대략|近似
local_time|Local time|Heure locale|Местное время|Yerel saat|Czas lokalny|Hora local|Hora local|Ortszeit|현지 시간|本地时间
server_time_short|server time|heure serveur|время сервера|sunucu saati|czas serwera|hora del servidor|hora do servidor|Serverzeit|서버 시간|服务器时间
snapshot_at|snapshot {time}|instantané {time}|снимок {time}|kayıt {time}|migawka {time}|captura {time}|captura {time}|Momentaufnahme {time}|스냅샷 {time}|快照 {time}
snapshot_server_time|Snapshot {time} server time|Instantané {time} heure serveur|Снимок {time} время сервера|Kayıt {time} sunucu saati|Migawka {time} czas serwera|Captura {time} hora del servidor|Captura {time} hora do servidor|Momentaufnahme {time} Serverzeit|스냅샷 {time} 서버 시간|快照 {time} 服务器时间
snapshot_window|Snapshot: {first} – {last} · server time (UTC−2)|Instantané : {first} – {last} · heure serveur (UTC−2)|Снимок: {first} – {last} · время сервера (UTC−2)|Kayıt: {first} – {last} · sunucu saati (UTC−2)|Migawka: {first} – {last} · czas serwera (UTC−2)|Captura: {first} – {last} · hora del servidor (UTC−2)|Captura: {first} – {last} · hora do servidor (UTC−2)|Momentaufnahme: {first} – {last} · Serverzeit (UTC−2)|스냅샷: {first} – {last} · 서버 시간 (UTC−2)|快照：{first} – {last} · 服务器时间（UTC−2）
source_screenshots|Screenshots|Captures d'écran|Снимки экрана|Ekran görüntüleri|Zrzuty ekranu|Capturas de pantalla|Capturas de ecrã|Bildschirmaufnahmen|캡처 화면|截图
source_capture_log|Capture log|Journal de capture|Журнал захвата|Kayıt günlüğü|Dziennik zapisu|Registro de captura|Registo de captura|Erfassungsprotokoll|캡처 로그|采集日志
source_legacy_file_times|Legacy file times|Dates des anciens fichiers|Время старых файлов|Eski dosya zamanları|Daty starych plików|Fechas de archivos antiguos|Datas dos ficheiros legados|Zeitstempel alter Dateien|기존 파일 타임스탬프|历史文件时间
week_by_week|Week by week|Semaine par semaine|По неделям|Haftadan haftaya|Tydzień po tygodniu|Semana a semana|Semana a semana|Woche für Woche|주간 기록|逐周记录
vs_week|VS week|Semaine VS|Неделя VS|VS haftası|Tydzień VS|Semana VS|Semana VS|VS-Woche|VS 주간|VS 周
steady|Steady|Régulier|Ровно|İstikrarlı|Równo|Constante|Constante|Gleichmäßig|꾸준함|稳定
uneven|Uneven|Irrégulier|Неровно|Dengesiz|Nierówno|Irregular|Irregular|Ungleichmäßig|들쭉날쭉|不均衡
spiky|Spiky|En pics|Скачками|Dalgalı|Skokowo|A picos|Aos picos|Sprunghaft|편중됨|起伏大
q_met|Met|Atteint|Выполнена|Ulaştı|Osiągnięty|Cumplido|Cumprida|Erfüllt|달성|达标
q_near|Near|Proche|Близко|Yakın|Blisko|Cerca|Perto|Knapp|근접|接近
q_below|Below|En dessous|Ниже|Altında|Poniżej|Por debajo|Abaixo|Darunter|미달|未达标
q_absent|Not in alliance|Hors de l'alliance|Не в альянсе|İttifakta değil|Poza sojuszem|Fuera de la alianza|Fora da aliança|Nicht in der Allianz|연맹 미소속|不在联盟
q_left|Left|Parti|Ушёл|Ayrıldı|Odszedł|Se fue|Saiu|Ausgetreten|탈퇴|已离开
q_missing|Not captured|Non capturé|Не записано|Kaydedilmedi|Nie zapisano|No capturado|Não capturado|Nicht erfasst|미수집|未采集
ins_quota_rate|{met} of {members} members ({rate}) reached the {quota} quota.|{met} membres sur {members} ({rate}) ont atteint l'objectif de {quota}.|{met} из {members} участников ({rate}) выполнили норму {quota}.|{members} üyeden {met} kişi ({rate}) {quota} hedefine ulaştı.|{met} z {members} członków ({rate}) osiągnęło cel {quota}.|{met} de {members} miembros ({rate}) alcanzaron el objetivo de {quota}.|{met} de {members} membros ({rate}) atingiram a meta de {quota}.|{met} von {members} Mitgliedern ({rate}) haben das Soll von {quota} erreicht.|멤버 {members}명 중 {met}명({rate})이 목표 {quota}를 달성했습니다.|{members} 名成员中有 {met} 名（{rate}）达到 {quota} 配额。
ins_rate_up|Up from {rate} on {date}.|En hausse par rapport à {rate} le {date}.|Больше, чем {date} ({rate}).|{date} tarihindeki {rate} oranından yüksek.|Więcej niż {rate} w dniu {date}.|Sube desde {rate} el {date}.|Acima dos {rate} de {date}.|Mehr als {rate} am {date}.|{date}의 {rate}보다 높습니다.|高于 {date} 的 {rate}。
ins_rate_down|Down from {rate} on {date}.|En baisse par rapport à {rate} le {date}.|Меньше, чем {date} ({rate}).|{date} tarihindeki {rate} oranından düşük.|Mniej niż {rate} w dniu {date}.|Baja desde {rate} el {date}.|Abaixo dos {rate} de {date}.|Weniger als {rate} am {date}.|{date}의 {rate}보다 낮습니다.|低于 {date} 的 {rate}。
ins_repeat|{n} members also fell short on {date}:|{n} membres étaient déjà en dessous le {date} :|{n} участников не выполнили норму и {date}:|{n} üye {date} tarihinde de hedefin altındaydı:|{n} członków nie osiągnęło celu także {date}:|{n} miembros tampoco llegaron el {date}:|{n} membros também ficaram abaixo em {date}:|{n} Mitglieder lagen auch am {date} darunter:|{n}명은 {date}에도 미달했습니다:|{n} 名成员在 {date} 也未达标：
ins_no_repeat|No one missed the quota both this week and on {date}.|Personne n'a manqué l'objectif cette semaine et le {date}.|Никто не провалил норму и на этой неделе, и {date}.|Kimse hem bu hafta hem de {date} tarihinde hedefi kaçırmadı.|Nikt nie chybił celu jednocześnie w tym tygodniu i {date}.|Nadie falló el objetivo esta semana y también el {date}.|Ninguém falhou a meta esta semana e também em {date}.|Niemand hat das Soll diese Woche und am {date} verfehlt.|이번 주와 {date} 모두 미달한 멤버는 없습니다.|没有成员在本周和 {date} 都未达标。
ins_low_days|{n} members scored on {days} days or fewer. Points on every day add up toward the quota.|{n} membres ont marqué sur {days} jours ou moins. Chaque jour compte pour l'objectif.|{n} участников набирали очки не более {days} дней. Очки каждого дня идут в норму.|{n} üye en fazla {days} gün puan aldı. Her günün puanı hedefe katkı sağlar.|{n} członków zdobywało punkty przez {days} dni lub mniej. Każdy dzień przybliża do celu.|{n} miembros puntuaron {days} días o menos. Cada día suma para el objetivo.|{n} membros pontuaram em {days} dias ou menos. Cada dia conta para a meta.|{n} Mitglieder punkteten an höchstens {days} Tagen. Jeder Tag zählt fürs Soll.|{n}명이 {days}일 이하만 점수를 얻었습니다. 매일의 점수가 목표에 더해집니다.|{n} 名成员仅在 {days} 天或更少的日子得分。每天的积分都计入配额。
ins_top10|The top 10 players scored {share} of the alliance's weekly points.|Les 10 meilleurs joueurs ont marqué {share} des points hebdomadaires de l'alliance.|Топ-10 игроков набрали {share} недельных очков альянса.|İlk 10 oyuncu ittifakın haftalık puanının {share} kadarını topladı.|Najlepsza 10 zdobyła {share} tygodniowych punktów sojuszu.|Los 10 mejores sumaron el {share} de los puntos semanales de la alianza.|Os 10 melhores somaram {share} dos pontos semanais da aliança.|Die besten 10 holten {share} der Wochenpunkte der Allianz.|상위 10명이 연맹 주간 포인트의 {share}를 기록했습니다.|前 10 名玩家贡献了联盟周积分的 {share}。
ins_margins|Biggest margin: {best} ({bestv}). Closest: {close} ({closev}).|Plus grand écart : {best} ({bestv}). Plus serré : {close} ({closev}).|Крупнейший отрыв: {best} ({bestv}). Самый близкий: {close} ({closev}).|En büyük fark: {best} ({bestv}). En yakın: {close} ({closev}).|Największa przewaga: {best} ({bestv}). Najbliżej: {close} ({closev}).|Mayor margen: {best} ({bestv}). Más ajustado: {close} ({closev}).|Maior margem: {best} ({bestv}). Mais renhido: {close} ({closev}).|Größter Vorsprung: {best} ({bestv}). Am knappsten: {close} ({closev}).|최대 격차: {best} ({bestv}). 최소 격차: {close} ({closev}).|最大分差：{best}（{bestv}）。最接近：{close}（{closev}）。
ins_turnout|Lowest turnout: {day}, with {n} of {members} members scoring.|Participation la plus faible : {day}, {n} membres sur {members} ont marqué.|Меньше всего участия: {day}, очки набрали {n} из {members}.|En düşük katılım: {day}, {members} üyeden {n} kişi puan aldı.|Najniższa frekwencja: {day}, punkty zdobyło {n} z {members}.|Menor participación: {day}, con {n} de {members} miembros puntuando.|Menor participação: {day}, com {n} de {members} membros a pontuar.|Geringste Beteiligung: {day}, {n} von {members} Mitgliedern punkteten.|최저 참여일: {day}, {members}명 중 {n}명이 점수를 얻었습니다.|参与最低：{day}，{members} 名成员中 {n} 名得分。
ins_roster|Roster change since {date}: {joined} new, {left} gone.|Effectif depuis le {date} : {joined} nouveaux, {left} partis.|Состав с {date}: новых {joined}, ушли {left}.|{date} tarihinden beri kadro: {joined} yeni, {left} ayrılan.|Zmiany składu od {date}: {joined} nowych, {left} odeszło.|Cambios desde el {date}: {joined} nuevos, {left} se fueron.|Mudanças desde {date}: {joined} novos, {left} saíram.|Kader seit {date}: {joined} neu, {left} weg.|{date} 이후 명단 변화: 신규 {joined}명, 이탈 {left}명.|自 {date} 以来的阵容变化：新增 {joined} 人，离开 {left} 人。
ins_live|This week is still running: totals and quota results can still change.|La semaine est en cours : les totaux et l'objectif peuvent encore changer.|Неделя ещё идёт: итоги и выполнение нормы могут измениться.|Hafta devam ediyor: toplamlar ve hedef sonuçları değişebilir.|Tydzień trwa: sumy i wyniki celu mogą się zmienić.|La semana sigue en curso: los totales y el objetivo aún pueden cambiar.|A semana ainda decorre: totais e metas ainda podem mudar.|Die Woche läuft noch: Summen und Soll-Ergebnisse können sich ändern.|이번 주는 아직 진행 중입니다. 합계와 목표 달성 여부가 바뀔 수 있습니다.|本周仍在进行中：总分和配额结果仍可能变化。
new_member|New|Nouveau|Новый|Yeni|Nowy|Nuevo|Novo|Neu|신규|新成员
missed_twice|Missed twice|Manqué deux fois|Не выполнил дважды|İki kez kaçırdı|Dwa razy poniżej|Fallado dos veces|Falhou duas vezes|Zweimal verfehlt|2회 연속 미달|连续两次未达标
quota_check|Quota check|Suivi de l'objectif|Проверка нормы|Hedef kontrolü|Kontrola celu|Control del objetivo|Controlo da meta|Soll-Check|목표 점검|配额检查
short_by|Short by|Manque|Не хватает|Eksik|Brakuje|Faltan|Faltam|Fehlt|부족분|差额
below_quota|Below quota|Sous l'objectif|Ниже нормы|Hedefin altında|Poniżej celu|Por debajo del objetivo|Abaixo da meta|Unter dem Soll|목표 미달|未达标
below_quota_so_far|Below quota so far|Sous l'objectif pour l'instant|Пока ниже нормы|Şimdilik hedefin altında|Na razie poniżej celu|Por debajo del objetivo por ahora|Abaixo da meta por agora|Bisher unter dem Soll|현재 목표 미달|目前未达标
everyone_met|Everyone reached the quota.|Tout le monde a atteint l'objectif.|Все выполнили норму.|Herkes hedefe ulaştı.|Wszyscy osiągnęli cel.|Todos alcanzaron el objetivo.|Todos atingiram a meta.|Alle haben das Soll erreicht.|모두 목표를 달성했습니다.|所有人都达到了配额。
see_record|Week-by-week record|Historique semaine par semaine|История по неделям|Haftalık geçmiş|Historia tydzień po tygodniu|Historial semana a semana|Histórico semana a semana|Verlauf Woche für Woche|주간 기록 보기|逐周记录
movers|Biggest movers|Plus fortes variations|Наибольшие изменения|En büyük değişimler|Największe zmiany|Mayores cambios|Maiores variações|Größte Veränderungen|가장 큰 변화|变化最大
vs_date|vs {date}|vs {date}|к {date}|{date} ile|vs {date}|vs {date}|vs {date}|ggü. {date}|{date} 대비|对比 {date}
biggest_gains|Gains|Hausses|Рост|Artışlar|Wzrosty|Subidas|Subidas|Zuwächse|상승|上升
biggest_drops|Drops|Baisses|Падение|Düşüşler|Spadki|Bajadas|Descidas|Rückgänge|하락|下降
of_alliance|of alliance points|des points de l'alliance|очков альянса|ittifak puanının|punktów sojuszu|de los puntos de la alianza|dos pontos da aliança|der Allianzpunkte|연맹 포인트 중|占联盟积分
quota_met_tile|Reached quota|Objectif atteint|Выполнили норму|Hedefe ulaşan|Osiągnęli cel|Alcanzaron el objetivo|Atingiram a meta|Soll erreicht|목표 달성|达到配额
full_attendance|Scored every day|Ont marqué chaque jour|Очки каждый день|Her gün puan alan|Punkty każdego dnia|Puntuaron cada día|Pontuaram todos os dias|Jeden Tag gepunktet|매일 득점|每天得分
all_days_hint|Points on every started stage|Des points à chaque étape commencée|Очки на каждом начатом этапе|Başlayan her aşamada puan|Punkty na każdym rozpoczętym etapie|Puntos en cada etapa iniciada|Pontos em cada etapa iniciada|Punkte in jeder begonnenen Etappe|시작된 모든 단계에서 득점|每个已开始阶段都有积分
top_performer|Top performer|Meilleur joueur|Лучший игрок|En iyi oyuncu|Najlepszy gracz|Mejor jugador|Melhor jogador|Bester Spieler|최고 성적|最佳玩家
wins_of|of {n} wins · {k} to clinch|sur {n} victoires · {k} pour gagner|из {n} побед · {k} для победы|{n} galibiyetten · {k} ile kesinleşir|z {n} wygranych · {k} zapewnia zwycięstwo|de {n} victorias · {k} para asegurar|de {n} vitórias · {k} para garantir|von {n} Siegen · {k} entscheiden|총 {n}승 중 · {k}승이면 확정|共 {n} 胜 · {k} 胜锁定
takeaways|Key takeaways|À retenir|Главное|Öne çıkanlar|Najważniejsze|Lo más destacado|Principais conclusões|Das Wichtigste|핵심 요약|要点
show_table|Show table|Afficher le tableau|Показать таблицу|Tabloyu göster|Pokaż tabelę|Mostrar tabla|Mostrar tabela|Tabelle anzeigen|표 보기|显示表格
not_captured|Week not captured|Semaine non capturée|Неделя не записана|Hafta kaydedilmedi|Tydzień nie został zapisany|Semana no capturada|Semana não capturada|Woche nicht erfasst|수집되지 않은 주|该周未采集
not_captured_short|No data|Aucune donnée|Нет данных|Veri yok|Brak danych|Sin datos|Sem dados|Keine Daten|데이터 없음|无数据
provisional|Provisional: the week is still running|Provisoire : la semaine est en cours|Предварительно: неделя ещё идёт|Geçici: hafta devam ediyor|Tymczasowe: tydzień trwa|Provisional: la semana sigue en curso|Provisório: a semana ainda decorre|Vorläufig: die Woche läuft noch|잠정: 이번 주 진행 중|暂定：本周仍在进行
quota_record|Quota record|Bilan objectif|История нормы|Hedef geçmişi|Bilans celu|Historial del objetivo|Histórico da meta|Soll-Bilanz|목표 달성 기록|配额记录
streak|Streak|Série|Серия|Seri|Seria|Racha|Sequência|Serie|연속|连续
n_players|{n} players|{n} joueurs|Игроков: {n}|{n} oyuncu|Graczy: {n}|{n} jugadores|{n} jogadores|{n} Spieler|플레이어 {n}명|{n} 名玩家
rf_all|All|Tous|Все|Tümü|Wszyscy|Todos|Todos|Alle|전체|全部
rf_below_selected|Below this week|Sous l'objectif cette semaine|Ниже нормы на этой неделе|Bu hafta altında|Poniżej w tym tygodniu|Por debajo esta semana|Abaixo esta semana|Diese Woche darunter|이번 주 미달|本周未达标
rf_missed_any|Missed any week|Au moins un échec|Хоть раз не выполнил|En az bir kez kaçıran|Choć raz poniżej|Falló alguna semana|Falhou alguma semana|Mindestens einmal verfehlt|한 번 이상 미달|曾未达标
rf_perfect|Never missed|Jamais manqué|Ни разу не провалил|Hiç kaçırmayan|Zawsze osiągał|Nunca falló|Nunca falhou|Nie verfehlt|미달 없음|从未未达标
rf_streak|On a streak|En série|В серии|Seride|Seria trwa|En racha|Em sequência|In Serie|연속 달성 중|连续达标中
record_intro|Every member, every tracked week. A week counts as met at {quota} weekly points or more. Select a name for a full profile with tips.|Chaque membre, chaque semaine suivie. Une semaine est réussie à partir de {quota} points hebdomadaires. Sélectionnez un nom pour son profil et des conseils.|Каждый участник, каждая записанная неделя. Норма выполнена при {quota} очков за неделю и больше. Выберите имя, чтобы открыть профиль с советами.|Her üye, takip edilen her hafta. Haftalık {quota} puan ve üzeri hedefe ulaşmış sayılır. Ayrıntılı profil ve ipuçları için bir isim seçin.|Każdy członek, każdy zapisany tydzień. Cel jest osiągnięty przy {quota} punktów tygodniowo lub więcej. Wybierz gracza, aby zobaczyć profil i wskazówki.|Cada miembro, cada semana registrada. Una semana cumple con {quota} puntos semanales o más. Elige un nombre para ver su perfil y consejos.|Cada membro, cada semana registada. Uma semana cumpre com {quota} pontos semanais ou mais. Escolha um nome para ver o perfil e dicas.|Jedes Mitglied, jede erfasste Woche. Eine Woche gilt ab {quota} Wochenpunkten als erfüllt. Wähle einen Namen für Profil und Tipps.|모든 멤버의 모든 주간 기록입니다. 주간 {quota} 포인트 이상이면 달성입니다. 이름을 선택하면 프로필과 팁을 볼 수 있습니다.|每位成员的每个记录周。周积分达到 {quota} 即为达标。点击名字查看完整资料和建议。
weeks_tracked|Weeks tracked|Semaines suivies|Записано недель|Takip edilen hafta|Zapisane tygodnie|Semanas registradas|Semanas registadas|Erfasste Wochen|기록된 주|记录周数
weeks_missing|Not captured: {n}|Non capturées : {n}|Не записано: {n}|Kaydedilmeyen: {n}|Niezapisane: {n}|No capturadas: {n}|Não capturadas: {n}|Nicht erfasst: {n}|미수집: {n}|未采集：{n}
weeks_since|Since {date}|Depuis le {date}|С {date}|{date} tarihinden beri|Od {date}|Desde el {date}|Desde {date}|Seit {date}|{date}부터|自 {date} 起
perfect_record|Never missed|Jamais manqué|Ни разу не провалили|Hiç kaçırmayan|Zawsze osiągali|Nunca fallaron|Nunca falharam|Nie verfehlt|미달 없음|从未未达标
perfect_hint|Met the quota every tracked week|Objectif atteint chaque semaine suivie|Норма выполнена каждую неделю|Takip edilen her hafta hedefe ulaştı|Cel osiągnięty w każdym tygodniu|Cumplieron todas las semanas registradas|Cumpriram todas as semanas registadas|Soll in jeder erfassten Woche erfüllt|기록된 모든 주에 목표 달성|每个记录周都达标
below_in_week|Below quota · {date}|Sous l'objectif · {date}|Ниже нормы · {date}|Hedefin altında · {date}|Poniżej celu · {date}|Por debajo · {date}|Abaixo da meta · {date}|Unter dem Soll · {date}|목표 미달 · {date}|未达标 · {date}
near_or_below|Near or below the quota|Proches ou sous l'objectif|Близко к норме или ниже|Hedefe yakın veya altında|Blisko lub poniżej celu|Cerca o por debajo del objetivo|Perto ou abaixo da meta|Knapp oder unter dem Soll|목표 근접 또는 미달|接近或未达标
repeat_misses|Missed 2+ weeks|Manqué 2+ semaines|Провалили 2+ недели|2+ hafta kaçıran|Poniżej 2+ tygodnie|Fallaron 2+ semanas|Falharam 2+ semanas|2+ Wochen verfehlt|2주 이상 미달|2 周以上未达标
repeat_hint|On a 2+ week streak: {n}|En série de 2+ semaines : {n}|Серия 2+ недели: {n}|2+ haftalık seride: {n}|Seria 2+ tygodni: {n}|En racha de 2+ semanas: {n}|Em sequência de 2+ semanas: {n}|2+ Wochen in Serie: {n}|2주 이상 연속 달성: {n}|连续达标 2 周以上：{n}
rs_selected|Sort: points on {date}|Tri : points du {date}|Сортировка: очки {date}|Sırala: {date} puanı|Sortuj: punkty {date}|Ordenar: puntos del {date}|Ordenar: pontos de {date}|Sortieren: Punkte am {date}|정렬: {date} 포인트|排序：{date} 积分
rs_record|Sort: most missed weeks|Tri : plus d'échecs|Сортировка: больше всего провалов|Sırala: en çok kaçırılan|Sortuj: najwięcej tygodni poniżej|Ordenar: más semanas fallidas|Ordenar: mais semanas falhadas|Sortieren: meiste Fehlwochen|정렬: 미달 많은 순|排序：未达标最多
rs_average|Sort: average|Tri : moyenne|Сортировка: среднее|Sırala: ortalama|Sortuj: średnia|Ordenar: promedio|Ordenar: média|Sortieren: Durchschnitt|정렬: 평균|排序：平均
rs_change|Sort: change vs previous week|Tri : variation vs semaine précédente|Сортировка: изменение к прошлой неделе|Sırala: önceki haftaya göre değişim|Sortuj: zmiana do poprzedniego tygodnia|Ordenar: cambio vs semana anterior|Ordenar: variação vs semana anterior|Sortieren: Veränderung zur Vorwoche|정렬: 전주 대비 변화|排序：较上周变化
rs_name|Sort: name|Tri : nom|Сортировка: имя|Sırala: isim|Sortuj: nazwa|Ordenar: nombre|Ordenar: nome|Sortieren: Name|정렬: 이름|排序：名称
show_former|Show former members|Afficher les anciens membres|Показать бывших участников|Eski üyeleri göster|Pokaż byłych członków|Mostrar exmiembros|Mostrar antigos membros|Ehemalige anzeigen|이전 멤버 표시|显示前成员
lg_met|Met: {n}+|Atteint : {n}+|Выполнена: {n}+|Ulaştı: {n}+|Osiągnięty: {n}+|Cumplido: {n}+|Cumprida: {n}+|Erfüllt: {n}+|달성: {n} 이상|达标：{n}+
lg_near|Near: {n}+|Proche : {n}+|Близко: {n}+|Yakın: {n}+|Blisko: {n}+|Cerca: {n}+|Perto: {n}+|Knapp: {n}+|근접: {n} 이상|接近：{n}+
lg_below|Below {n}|Sous {n}|Ниже {n}|{n} altı|Poniżej {n}|Menos de {n}|Abaixo de {n}|Unter {n}|{n} 미만|低于 {n}
record_note|Dashed outline = provisional (week still running).|Contour pointillé = provisoire (semaine en cours).|Пунктир = предварительно (неделя идёт).|Kesikli çerçeve = geçici (hafta sürüyor).|Przerywana ramka = tymczasowe (tydzień trwa).|Borde discontinuo = provisional (semana en curso).|Contorno tracejado = provisório (semana a decorrer).|Gestrichelt = vorläufig (Woche läuft).|점선 = 잠정(주간 진행 중).|虚线框 = 暂定（本周进行中）。
heat_low|Low|Faible|Мало|Düşük|Mało|Bajo|Baixo|Wenig|낮음|低
heat_high|High|Élevé|Много|Yüksek|Dużo|Alto|Alto|Viel|높음|高
heat_hint|Shading compares each day with that day's alliance median; gold outline = best day.|La teinte compare chaque jour à la médiane de l'alliance ; contour doré = meilleur jour.|Оттенок сравнивает день с медианой альянса за этот день; золотая рамка — лучший день.|Renk tonu her günü o günün ittifak medyanıyla karşılaştırır; altın çerçeve = en iyi gün.|Odcień porównuje dzień z medianą sojuszu z tego dnia; złota ramka = najlepszy dzień.|El sombreado compara cada día con la mediana de la alianza; borde dorado = mejor día.|O sombreado compara cada dia com a mediana da aliança; contorno dourado = melhor dia.|Die Färbung vergleicht jeden Tag mit dem Allianz-Median des Tages; Goldrand = bester Tag.|음영은 그날의 연맹 중앙값과 비교합니다. 금색 테두리 = 최고의 날.|颜色深浅对比当天的联盟中位数；金色边框 = 最佳日。
vs_last|vs last week|vs semaine précédente|к прошлой неделе|geçen haftaya göre|vs poprzedni tydzień|vs semana anterior|vs semana anterior|ggü. Vorwoche|전주 대비|较上周
balance|Daily balance|Équilibre quotidien|Равномерность|Günlük denge|Rozkład dzienny|Equilibrio diario|Equilíbrio diário|Tagesbalance|일별 균형|每日均衡
balance_hint|How evenly points are spread across the days, relative to each day's alliance median.|Répartition des points sur les jours, par rapport à la médiane de l'alliance de chaque jour.|Насколько равномерно очки распределены по дням относительно медианы альянса.|Puanların günlere ne kadar dengeli dağıldığı (her günün ittifak medyanına göre).|Jak równo punkty rozkładają się na dni względem mediany sojuszu.|Qué tan repartidos están los puntos entre los días, respecto a la mediana diaria de la alianza.|Quão distribuídos estão os pontos pelos dias, face à mediana diária da aliança.|Wie gleichmäßig die Punkte über die Tage verteilt sind, relativ zum Tages-Median der Allianz.|그날 연맹 중앙값 대비 포인트가 며칠에 걸쳐 얼마나 고르게 분포되었는지.|相对于每天联盟中位数，积分在各天分布的均衡程度。
new_short|New|Nouveau|Новый|Yeni|Nowy|Nuevo|Novo|Neu|신규|新
median|median|médiane|медиана|medyan|mediana|mediana|mediana|Median|중앙값|中位数
median_player|Median player|Joueur médian|Медианный игрок|Medyan oyuncu|Mediana gracza|Jugador mediano|Jogador mediano|Median-Spieler|중앙값 플레이어|中位玩家
leaderboards_intro|Full server leaderboards for every day and the week, as captured.|Classements complets du serveur pour chaque jour et la semaine, tels que capturés.|Полные серверные рейтинги за каждый день и неделю, как записано.|Her gün ve hafta için kaydedildiği hâliyle tam sunucu sıralamaları.|Pełne rankingi serwera dla każdego dnia i tygodnia, jak zapisano.|Clasificaciones completas del servidor por día y semana, tal como se capturaron.|Classificações completas do servidor por dia e semana, tal como capturadas.|Vollständige Server-Ranglisten für jeden Tag und die Woche, wie erfasst.|캡처한 그대로의 일별·주간 전체 서버 순위표입니다.|按采集结果展示每天和整周的完整服务器排行榜。
trends_intro|How the alliance performs across weeks: points, quota compliance and stage results.|Performance de l'alliance au fil des semaines : points, respect de l'objectif et étapes.|Как альянс выступает из недели в неделю: очки, выполнение нормы и этапы.|İttifakın haftalar boyunca performansı: puanlar, hedef uyumu ve aşama sonuçları.|Wyniki sojuszu w kolejnych tygodniach: punkty, realizacja celu i etapy.|Rendimiento de la alianza semana a semana: puntos, cumplimiento del objetivo y etapas.|Desempenho da aliança ao longo das semanas: pontos, cumprimento da meta e etapas.|Wie die Allianz über die Wochen abschneidet: Punkte, Soll-Erfüllung und Etappen.|주간별 연맹 성과: 포인트, 목표 달성률, 단계 결과.|联盟逐周表现：积分、配额达标率和阶段结果。
members_intro|This week's roster: daily points, quota status and how evenly each member contributed.|Effectif de la semaine : points par jour, objectif et régularité de chaque membre.|Состав недели: очки по дням, норма и равномерность вклада каждого.|Bu haftanın kadrosu: günlük puanlar, hedef durumu ve her üyenin ne kadar dengeli katkı verdiği.|Skład tygodnia: punkty dzienne, status celu i równomierność wkładu.|Plantilla de la semana: puntos diarios, estado del objetivo y regularidad de cada miembro.|Plantel da semana: pontos diários, estado da meta e regularidade de cada membro.|Kader dieser Woche: Tagespunkte, Soll-Status und wie gleichmäßig jedes Mitglied beitrug.|이번 주 명단: 일별 포인트, 목표 상태, 멤버별 기여 균형.|本周阵容：每日积分、配额状态以及每位成员贡献的均衡度。
opponent_intro|Scouting report on this week's opponent.|Rapport d'éclaireur sur l'adversaire de la semaine.|Разведка соперника этой недели.|Bu haftanın rakibi hakkında keşif raporu.|Raport zwiadowczy o rywalu tygodnia.|Informe de exploración del rival de la semana.|Relatório de reconhecimento do adversário da semana.|Aufklärung über den Gegner dieser Woche.|이번 주 상대 정찰 보고서.|本周对手侦察报告。
avg_compliance|Average quota compliance|Respect moyen de l'objectif|Среднее выполнение нормы|Ortalama hedef uyumu|Średnia realizacja celu|Cumplimiento medio del objetivo|Cumprimento médio da meta|Durchschnittliche Soll-Erfüllung|평균 목표 달성률|平均配额达标率
avg_weekly_points|Average weekly points|Points hebdomadaires moyens|Средние очки за неделю|Ortalama haftalık puan|Średnie punkty tygodniowe|Puntos semanales medios|Pontos semanais médios|Durchschnittliche Wochenpunkte|평균 주간 포인트|平均周积分
quota_by_week|Quota compliance by week|Respect de l'objectif par semaine|Выполнение нормы по неделям|Haftalara göre hedef uyumu|Realizacja celu według tygodni|Cumplimiento del objetivo por semana|Cumprimento da meta por semana|Soll-Erfüllung je Woche|주별 목표 달성률|每周配额达标率
pi_met|Quota reached with {surplus} to spare (quota {quota}).|Objectif atteint avec {surplus} de marge (objectif {quota}).|Норма выполнена с запасом {surplus} (норма {quota}).|Hedefe {surplus} fazlasıyla ulaşıldı (hedef {quota}).|Cel osiągnięty z zapasem {surplus} (cel {quota}).|Objetivo alcanzado con {surplus} de margen (objetivo {quota}).|Meta atingida com {surplus} de folga (meta {quota}).|Soll mit {surplus} Puffer erreicht (Soll {quota}).|목표({quota})를 {surplus} 여유 있게 달성했습니다.|已达标，超出 {surplus}（配额 {quota}）。
pi_short|Finished {deficit} short of the {quota} quota.|A terminé à {deficit} de l'objectif de {quota}.|Не хватило {deficit} до нормы {quota}.|{quota} hedefine {deficit} eksikle bitirdi.|Zabrakło {deficit} do celu {quota}.|Terminó a {deficit} del objetivo de {quota}.|Terminou a {deficit} da meta de {quota}.|{deficit} unter dem Soll von {quota} geblieben.|목표 {quota}에 {deficit} 부족했습니다.|距离 {quota} 配额还差 {deficit}。
pi_needs|Needs {deficit} more to reach the {quota} quota before the week ends.|Il manque {deficit} pour atteindre l'objectif de {quota} avant la fin de la semaine.|Нужно ещё {deficit} до нормы {quota} до конца недели.|Hafta bitmeden {quota} hedefine ulaşmak için {deficit} daha gerekiyor.|Potrzeba jeszcze {deficit} do celu {quota} przed końcem tygodnia.|Faltan {deficit} para alcanzar el objetivo de {quota} antes de que acabe la semana.|Faltam {deficit} para atingir a meta de {quota} antes do fim da semana.|Bis Wochenende fehlen noch {deficit} zum Soll von {quota}.|이번 주가 끝나기 전에 목표 {quota}까지 {deficit}가 더 필요합니다.|本周结束前还需 {deficit} 才能达到 {quota} 配额。
pi_missed|No points on {days}. Every stage counts: even a modest score each day adds up.|Aucun point le {days}. Chaque étape compte : même un petit score chaque jour s'additionne.|Нет очков: {days}. Каждый этап важен — даже немного очков в день складывается.|{days} günü puan yok. Her aşama önemli: her gün küçük bir puan bile birikir.|Brak punktów: {days}. Każdy etap się liczy, nawet niewielki wynik każdego dnia się sumuje.|Sin puntos el {days}. Cada etapa cuenta: incluso poco cada día suma.|Sem pontos em {days}. Cada etapa conta: mesmo pouco por dia soma.|Keine Punkte am {days}. Jede Etappe zählt: auch kleine Beiträge pro Tag summieren sich.|{days}에 점수가 없습니다. 모든 단계가 중요합니다. 매일 조금씩이라도 쌓입니다.|{days} 没有积分。每个阶段都重要：每天哪怕少量积分也会累积。
pi_best|Strongest stage: {stage} ({day}), {x}× the alliance median.|Meilleure étape : {stage} ({day}), {x}× la médiane de l'alliance.|Сильнейший этап: {stage} ({day}), {x}× медианы альянса.|En güçlü aşama: {stage} ({day}), ittifak medyanının {x} katı.|Najmocniejszy etap: {stage} ({day}), {x}× mediany sojuszu.|Mejor etapa: {stage} ({day}), {x}× la mediana de la alianza.|Melhor etapa: {stage} ({day}), {x}× a mediana da aliança.|Stärkste Etappe: {stage} ({day}), {x}× Allianz-Median.|가장 강한 단계: {stage}({day}), 연맹 중앙값의 {x}배.|最强阶段：{stage}（{day}），为联盟中位数的 {x} 倍。
pi_best_low|Closest to the alliance median: {stage} ({day}) at {x}×. Every other stage is further below it.|Le plus proche de la médiane de l'alliance : {stage} ({day}) à {x}×. Les autres étapes sont plus loin en dessous.|Ближе всего к медиане альянса: {stage} ({day}), {x}×. Остальные этапы ещё ниже.|İttifak medyanına en yakın: {stage} ({day}), {x} kat. Diğer aşamalar daha da altında.|Najbliżej mediany sojuszu: {stage} ({day}), {x}×. Pozostałe etapy są jeszcze niżej.|Lo más cerca de la mediana de la alianza: {stage} ({day}) con {x}×. Las demás etapas quedan más abajo.|O mais perto da mediana da aliança: {stage} ({day}) com {x}×. As restantes etapas ficam mais abaixo.|Am nächsten am Allianz-Median: {stage} ({day}) mit {x}×. Alle anderen Etappen liegen weiter darunter.|연맹 중앙값에 가장 가까운 단계: {stage}({day}), {x}배. 나머지 단계는 더 낮습니다.|最接近联盟中位数：{stage}（{day}），为 {x} 倍。其他阶段更低。
won_by|{name} won|Victoire de {name}|{name} победил|{name} kazandı|{name} wygrywa|{name} ganó|{name} venceu|{name} hat gewonnen|{name} 승리|{name} 获胜
snapshot_final_note|Rankings are read shortly before the midnight reset (server time, UTC−2). Once the week ends the lists disappear in game, so this snapshot is the week's final record.|Les classements sont relevés peu avant la réinitialisation de minuit (heure serveur, UTC−2). Une fois la semaine terminée, les listes disparaissent du jeu : cet instantané est donc le résultat final de la semaine.|Рейтинги снимаются незадолго до сброса в полночь (время сервера, UTC−2). После окончания недели списки исчезают из игры, поэтому этот снимок — итог недели.|Sıralamalar gece yarısı sıfırlamasından kısa süre önce okunur (sunucu saati, UTC−2). Hafta bitince listeler oyundan kalkar; bu kayıt haftanın nihai sonucudur.|Rankingi są odczytywane tuż przed resetem o północy (czas serwera, UTC−2). Po zakończeniu tygodnia listy znikają z gry, więc ta migawka jest końcowym wynikiem tygodnia.|Las clasificaciones se leen poco antes del reinicio de medianoche (hora del servidor, UTC−2). Al terminar la semana, las listas desaparecen del juego, así que esta captura es el resultado final de la semana.|As classificações são lidas pouco antes do reinício da meia-noite (hora do servidor, UTC−2). Quando a semana termina, as listas desaparecem do jogo, por isso esta captura é o resultado final da semana.|Die Ranglisten werden kurz vor dem Reset um Mitternacht (Serverzeit, UTC−2) erfasst. Nach Wochenende verschwinden die Listen im Spiel, daher ist diese Momentaufnahme das Endergebnis der Woche.|순위는 자정 초기화(서버 시간, UTC−2) 직전에 수집합니다. 주간이 끝나면 게임에서 순위표가 사라지므로 이 스냅샷이 해당 주의 최종 기록입니다.|排行榜在午夜重置（服务器时间 UTC−2）前不久采集。本周结束后游戏内榜单会消失，因此该快照即为本周最终记录。
rescanned|Rescanned|Relu|Пересканировано|Yeniden tarandı|Ponownie skanowano|Reescaneado|Reanalisado|Erneut gescannt|재스캔|已重扫
changed_during_capture|Changed during capture|Modifié pendant la capture|Изменилось при съёмке|Kayıt sırasında değişti|Zmieniło się podczas zapisu|Cambió durante la captura|Mudou durante a captura|Während der Erfassung geändert|수집 중 변경|采集期间变动
stage_5_short|Full Military Prep|Prépa militaire complète|Полная военная подг.|Tam askerî hazırlık|Pełne przyg. wojskowe|Prep. militar completa|Prep. militar completa|Militärvorbereitung|전면 군사 준비|全面军事准备
achievements|Achievements|Succès|Достижения|Başarımlar|Osiągnięcia|Logros|Conquistas|Erfolge|업적|成就
achievements_sub|{n} badges earned by {m} players this week|{n} badges obtenus par {m} joueurs cette semaine|{n} значков у {m} игроков на этой неделе|Bu hafta {m} oyuncu {n} rozet kazandı|{n} odznak zdobytych przez {m} graczy w tym tygodniu|{n} insignias ganadas por {m} jugadores esta semana|{n} insígnias conquistadas por {m} jogadores esta semana|{n} Abzeichen für {m} Spieler diese Woche|이번 주 {m}명이 배지 {n}종 획득|本周 {m} 名玩家获得 {n} 种徽章
rarity_legendary|Legendary|Légendaire|Легендарное|Efsanevi|Legendarne|Legendario|Lendário|Legendär|전설|传奇
rarity_rare|Rare|Rare|Редкое|Nadir|Rzadkie|Raro|Raro|Selten|희귀|稀有
rarity_common|Common|Courant|Обычное|Yaygın|Zwykłe|Común|Comum|Häufig|일반|普通
within_reach|Within reach|À portée de main|Совсем близко|Ulaşılabilir|W zasięgu|Al alcance|Ao alcance|In Reichweite|달성 임박|即将达成
no_badges|No badges this week yet.|Aucun badge cette semaine pour l'instant.|На этой неделе значков пока нет.|Bu hafta henüz rozet yok.|W tym tygodniu jeszcze bez odznak.|Aún sin insignias esta semana.|Ainda sem insígnias esta semana.|Diese Woche noch keine Abzeichen.|이번 주에는 아직 배지가 없습니다.|本周暂无徽章。
more_holders|+{n} more|+{n} autres|ещё {n}|+{n} kişi daha|+{n} więcej|+{n} más|+{n} mais|+{n} weitere|외 {n}명|另有 {n} 人
hint_six|Score on {days} too.|Marquer aussi le {days}.|Наберите очки и в {days}.|{days} günü de puan alın.|Zdobądź punkty także w {days}.|Puntúa también el {days}.|Pontue também em {days}.|Auch am {days} punkten.|{days}에도 점수를 얻으세요.|在 {days} 也拿到积分。
hint_all_rounder|Beat the alliance median on {days}.|Dépasser la médiane de l'alliance le {days}.|Превзойдите медиану альянса в {days}.|{days} günü ittifak medyanını geçin.|Pobij medianę sojuszu w {days}.|Supera la mediana de la alianza el {days}.|Supere a mediana da aliança em {days}.|Am {days} den Allianz-Median schlagen.|{days}에 연맹 중앙값을 넘으세요.|在 {days} 超过联盟中位数。
hint_streak|Meet the quota {n} more week(s) in a row.|Atteindre l'objectif encore {n} semaine(s) d'affilée.|Выполните норму ещё {n} нед. подряд.|Hedefe art arda {n} hafta daha ulaşın.|Osiągnij cel jeszcze {n} tydz. z rzędu.|Cumple el objetivo {n} semana(s) más seguidas.|Cumpra a meta mais {n} semana(s) seguidas.|Das Soll noch {n} Woche(n) in Folge erfüllen.|{n}주 더 연속으로 목표를 달성하세요.|再连续 {n} 周达标。
hint_points|{n} more points.|Encore {n} points.|Ещё {n} очков.|{n} puan daha.|Jeszcze {n} pkt.|{n} puntos más.|Mais {n} pontos.|Noch {n} Punkte.|{n} 포인트 더.|还差 {n} 积分。
hint_comeback|Meet the quota next week.|Atteindre l'objectif la semaine prochaine.|Выполните норму на следующей неделе.|Gelecek hafta hedefe ulaşın.|Osiągnij cel w przyszłym tygodniu.|Cumple el objetivo la próxima semana.|Cumpra a meta na próxima semana.|Nächste Woche das Soll erfüllen.|다음 주에 목표를 달성하세요.|下周达到配额。
badge_mvp|Week MVP|MVP de la semaine|MVP недели|Haftanın MVP'si|MVP tygodnia|MVP de la semana|MVP da semana|MVP der Woche|주간 MVP|周 MVP
badge_mvp_d|#1 in the alliance for the week.|N°1 de l'alliance sur la semaine.|№1 в альянсе за неделю.|Haftanın ittifak birincisi.|Nr 1 w sojuszu w tym tygodniu.|N.º 1 de la alianza en la semana.|N.º 1 da aliança na semana.|Platz 1 der Allianz in dieser Woche.|이번 주 연맹 1위.|本周联盟第一。
badge_server_first|Server #1|N°1 du serveur|№1 сервера|Sunucu birincisi|Nr 1 serwera|N.º 1 del servidor|N.º 1 do servidor|Server-Platz 1|서버 1위|全服第一
badge_server_first_d|Topped the whole server board on a day.|En tête de tout le classement serveur sur une journée.|Возглавил общий рейтинг сервера за день.|Bir gün tüm sunucu sıralamasında zirvede.|Prowadził w całym rankingu serwera danego dnia.|Lideró la clasificación del servidor un día.|Liderou a classificação do servidor num dia.|An einem Tag Spitze der gesamten Server-Rangliste.|하루 동안 서버 전체 순위표 1위.|某天登顶全服排行榜。
badge_stage_mvp|Stage MVP|MVP d'étape|MVP этапа|Aşama MVP'si|MVP etapu|MVP de etapa|MVP de etapa|Etappen-MVP|단계 MVP|阶段 MVP
badge_stage_mvp_d|Top scorer in the alliance on a day.|Meilleur score de l'alliance sur une journée.|Лучший в альянсе за день.|Bir gün ittifakın en çok puan alanı.|Najlepszy wynik w sojuszu danego dnia.|Máximo anotador de la alianza en un día.|Melhor pontuação da aliança num dia.|Bester der Allianz an einem Tag.|하루 연맹 최고 득점.|某天联盟得分最高。
badge_giant_slayer|Giant Slayer|Tueur de géants|Убийца гигантов|Dev avcısı|Pogromca gigantów|Matagigantes|Mata-gigantes|Riesentöter|거인 사냥꾼|屠巨者
badge_giant_slayer_d|Outscored the opponent's best player for the week.|A dépassé le meilleur joueur adverse sur la semaine.|Набрал больше лучшего игрока соперника за неделю.|Haftalık puanda rakibin en iyi oyuncusunu geçti.|Pokonał najlepszego gracza rywala w tygodniu.|Superó al mejor jugador rival en la semana.|Superou o melhor jogador adversário na semana.|Mehr Wochenpunkte als der beste Gegner.|상대 최고 플레이어보다 주간 점수가 높음.|周积分超过对手最佳玩家。
badge_server_top10|Server Top 10|Top 10 serveur|Топ-10 сервера|Sunucu ilk 10|Top 10 serwera|Top 10 del servidor|Top 10 do servidor|Server-Top-10|서버 상위 10|全服前十
badge_server_top10_d|Top 10 on the weekly server board.|Dans le top 10 du classement hebdomadaire du serveur.|В топ-10 недельного рейтинга сервера.|Haftalık sunucu sıralamasında ilk 10.|W top 10 tygodniowego rankingu serwera.|Top 10 de la clasificación semanal del servidor.|Top 10 da classificação semanal do servidor.|Top 10 der Wochen-Rangliste des Servers.|서버 주간 순위 상위 10위.|全服周榜前十。
badge_ten_times|Ten Times Over|Dix fois l'objectif|Десять норм|On kat|Dziesięć razy więcej|Diez veces más|Dez vezes mais|Zehnfach|10배 달성|十倍达标
badge_ten_times_d|10× the weekly quota or more.|10× l'objectif hebdomadaire ou plus.|10× недельной нормы и больше.|Haftalık hedefin 10 katı veya fazlası.|10× tygodniowego celu lub więcej.|10× el objetivo semanal o más.|10× a meta semanal ou mais.|Mindestens das 10-fache des Wochensolls.|주간 목표의 10배 이상.|周配额的 10 倍或以上。
badge_unstoppable|Unstoppable|Inarrêtable|Неудержимый|Durdurulamaz|Nie do zatrzymania|Imparable|Imparável|Unaufhaltsam|멈출 수 없는|势不可挡
badge_unstoppable_d|Met the quota 5+ weeks in a row.|Objectif atteint 5 semaines d'affilée ou plus.|Норма 5+ недель подряд.|Art arda 5+ hafta hedefe ulaştı.|Cel osiągnięty 5+ tygodni z rzędu.|Objetivo cumplido 5+ semanas seguidas.|Meta cumprida 5+ semanas seguidas.|Soll 5+ Wochen in Folge erfüllt.|5주 이상 연속 목표 달성.|连续 5 周以上达标。
badge_hat_trick|Hat Trick|Coup du chapeau|Хет-трик|Hat-trick|Hat-trick|Triplete|Hat-trick|Hattrick|해트트릭|帽子戏法
badge_hat_trick_d|Met the quota 3+ weeks in a row.|Objectif atteint 3 semaines d'affilée ou plus.|Норма 3+ недели подряд.|Art arda 3+ hafta hedefe ulaştı.|Cel osiągnięty 3+ tygodnie z rzędu.|Objetivo cumplido 3+ semanas seguidas.|Meta cumprida 3+ semanas seguidas.|Soll 3+ Wochen in Folge erfüllt.|3주 이상 연속 목표 달성.|连续 3 周以上达标。
badge_saturday_hero|Saturday Hero|Héros du samedi|Герой субботы|Cumartesi kahramanı|Bohater soboty|Héroe del sábado|Herói de sábado|Samstagsheld|토요일의 영웅|周六英雄
badge_saturday_hero_d|3× the alliance median on Saturday, the 4-win day.|3× la médiane de l'alliance le samedi, le jour à 4 victoires.|3× медианы альянса в субботу — день на 4 победы.|4 galibiyetlik cumartesi günü ittifak medyanının 3 katı.|3× mediany sojuszu w sobotę, dzień za 4 wygrane.|3× la mediana de la alianza el sábado, el día de 4 victorias.|3× a mediana da aliança no sábado, o dia de 4 vitórias.|3× Allianz-Median am Samstag, dem 4-Siege-Tag.|4승이 걸린 토요일에 연맹 중앙값의 3배.|在价值 4 胜的周六达到联盟中位数的 3 倍。
badge_all_rounder|All-Rounder|Polyvalent|Универсал|Çok yönlü|Wszechstronny|Todoterreno|Polivalente|Allrounder|올라운더|全能选手
badge_all_rounder_d|Above the alliance median on all six days.|Au-dessus de la médiane de l'alliance les six jours.|Выше медианы альянса все шесть дней.|Altı günün hepsinde ittifak medyanının üstünde.|Powyżej mediany sojuszu przez wszystkie sześć dni.|Por encima de la mediana de la alianza los seis días.|Acima da mediana da aliança nos seis dias.|An allen sechs Tagen über dem Allianz-Median.|6일 모두 연맹 중앙값 이상.|六天全部高于联盟中位数。
badge_metronome|Metronome|Métronome|Метроном|Metronom|Metronom|Metrónomo|Metrónomo|Metronom|메트로놈|节拍器
badge_metronome_d|Scored every day, evenly across all six.|A marqué chaque jour, de façon régulière sur les six.|Набирал очки каждый день и ровно.|Her gün ve altı güne dengeli puan aldı.|Punktował codziennie, równo przez sześć dni.|Puntuó cada día, de forma pareja los seis.|Pontuou todos os dias, de forma equilibrada.|Jeden Tag gepunktet, gleichmäßig über alle sechs.|매일 고르게 득점.|每天得分且六天均衡。
badge_glow_up|Glow Up|Métamorphose|Рывок|Parlama|Metamorfoza|Gran salto|Grande salto|Durchstarter|급성장|华丽蜕变
badge_glow_up_d|Up 50%+ on last week and met the quota.|+50 % ou plus par rapport à la semaine dernière, objectif atteint.|+50% и больше к прошлой неделе, норма выполнена.|Geçen haftaya göre %50+ artış ve hedefe ulaştı.|+50% lub więcej względem zeszłego tygodnia i cel osiągnięty.|+50 % o más que la semana pasada y objetivo cumplido.|+50% ou mais face à semana passada e meta cumprida.|+50 % oder mehr ggü. Vorwoche und Soll erfüllt.|전주 대비 50% 이상 상승하고 목표 달성.|较上周提升 50% 以上并达标。
badge_climber|Climber|Grimpeur|Скалолаз|Tırmanıcı|Wspinacz|Escalador|Escalador|Aufsteiger|등반가|攀登者
badge_climber_d|Rose 10+ places in the alliance since last week.|A gagné 10 places ou plus dans l'alliance depuis la semaine dernière.|Поднялся на 10+ мест в альянсе с прошлой недели.|Geçen haftadan beri ittifakta 10+ sıra yükseldi.|Awans o 10+ miejsc w sojuszu od zeszłego tygodnia.|Subió 10+ puestos en la alianza desde la semana pasada.|Subiu 10+ posições na aliança desde a semana passada.|Seit letzter Woche 10+ Plätze in der Allianz gestiegen.|지난주보다 연맹 순위 10계단 이상 상승.|较上周在联盟内上升 10 名以上。
badge_comeback|Comeback|Retour en force|Камбэк|Geri dönüş|Powrót|Remontada|Reviravolta|Comeback|컴백|逆袭
badge_comeback_d|Below quota last week, met it this week.|Sous l'objectif la semaine dernière, atteint cette semaine.|На прошлой неделе ниже нормы, на этой — выполнена.|Geçen hafta hedefin altında, bu hafta ulaştı.|W zeszłym tygodniu poniżej celu, w tym osiągnięty.|Por debajo la semana pasada, cumplido esta semana.|Abaixo na semana passada, cumprida esta semana.|Letzte Woche unter dem Soll, diese Woche erfüllt.|지난주 미달, 이번 주 달성.|上周未达标，本周达标。
badge_strong_debut|Strong Debut|Débuts réussis|Яркий дебют|Güçlü başlangıç|Mocny debiut|Gran debut|Grande estreia|Starkes Debüt|화려한 데뷔|首秀出色
badge_strong_debut_d|New this week and met the quota.|Nouveau cette semaine et objectif atteint.|Новичок недели, норма выполнена.|Bu hafta yeni ve hedefe ulaştı.|Nowy w tym tygodniu i cel osiągnięty.|Nuevo esta semana y objetivo cumplido.|Novo esta semana e meta cumprida.|Neu diese Woche und Soll erfüllt.|이번 주 신규, 목표 달성.|本周新成员且达标。
badge_buzzer_beater|Buzzer Beater|Au buzzer|На последней секунде|Son saniye|Na ostatnią chwilę|Sobre la bocina|No último segundo|Last-Second-Treffer|버저비터|绝杀
badge_buzzer_beater_d|Reached the quota on Saturday, the last day.|A atteint l'objectif le samedi, dernier jour.|Выполнил норму в субботу, в последний день.|Hedefe son gün olan cumartesi ulaştı.|Osiągnął cel w sobotę, ostatniego dnia.|Alcanzó el objetivo el sábado, el último día.|Atingiu a meta no sábado, o último dia.|Das Soll am Samstag, dem letzten Tag, erreicht.|마지막 날인 토요일에 목표 달성.|在最后一天周六达标。
badge_photo_finish|Photo Finish|Photo-finish|Фотофиниш|Foto finiş|Fotofinisz|Foto finish|Fotofinish|Fotofinish|포토 피니시|险胜
badge_photo_finish_d|Met the quota with less than 5% to spare.|Objectif atteint avec moins de 5 % de marge.|Норма выполнена с запасом меньше 5%.|Hedefe %5'ten az farkla ulaştı.|Cel osiągnięty z zapasem poniżej 5%.|Objetivo cumplido con menos del 5 % de margen.|Meta cumprida com menos de 5% de folga.|Soll mit weniger als 5 % Puffer erfüllt.|5% 미만의 여유로 목표 달성.|以不到 5% 的余量达标。
badge_personal_best|Personal Best|Record personnel|Личный рекорд|Kişisel rekor|Rekord życiowy|Mejor marca personal|Recorde pessoal|Persönliche Bestleistung|개인 최고 기록|个人最佳
badge_personal_best_d|Highest weekly total of all tracked weeks.|Meilleur total hebdomadaire de toutes les semaines suivies.|Лучший недельный результат за все записанные недели.|Takip edilen haftaların en yüksek haftalık toplamı.|Najwyższy wynik tygodniowy ze wszystkich zapisanych tygodni.|Mejor total semanal de todas las semanas registradas.|Melhor total semanal de todas as semanas registadas.|Höchste Wochensumme aller erfassten Wochen.|기록된 모든 주 중 최고 주간 합계.|所有记录周中的最高周积分。
badge_six_for_six|Six for Six|Six sur six|Шесть из шести|Altıda altı|Sześć na sześć|Seis de seis|Seis em seis|Sechs von sechs|6일 개근|六天全勤
badge_six_for_six_d|Scored on all six days.|A marqué les six jours.|Набирал очки все шесть дней.|Altı günün hepsinde puan aldı.|Punktował wszystkie sześć dni.|Puntuó los seis días.|Pontuou nos seis dias.|An allen sechs Tagen gepunktet.|6일 모두 득점.|六天全部得分。
pi_grow|Most room to grow: {stage} ({day}) at {x}× the median. Points come from: {how}|Plus grande marge de progression : {stage} ({day}) à {x}× la médiane. Points obtenus via : {how}|Больше всего резерва: {stage} ({day}), {x}× медианы. Очки дают: {how}|En çok gelişme alanı: {stage} ({day}), medyanın {x} katı. Puan kaynakları: {how}|Największe pole do poprawy: {stage} ({day}), {x}× mediany. Punkty za: {how}|Mayor margen de mejora: {stage} ({day}) con {x}× la mediana. Los puntos vienen de: {how}|Maior margem de melhoria: {stage} ({day}) com {x}× a mediana. Os pontos vêm de: {how}|Größtes Potenzial: {stage} ({day}) mit {x}× Median. Punkte gibt es für: {how}|가장 성장 여지가 큰 단계: {stage}({day}), 중앙값의 {x}배. 포인트 획득: {how}|最大提升空间：{stage}（{day}），为中位数的 {x} 倍。积分来源：{how}
pi_sat|Saturday is worth 4 of the 13 wins, so it matters most.|Le samedi vaut 4 des 13 victoires : c'est le jour le plus important.|Суббота даёт 4 из 13 побед — это самый важный день.|Cumartesi 13 galibiyetin 4'ünü verir; en önemli gündür.|Sobota daje 4 z 13 wygranych, więc liczy się najbardziej.|El sábado vale 4 de las 13 victorias: es el día clave.|O sábado vale 4 das 13 vitórias: é o dia mais importante.|Der Samstag bringt 4 von 13 Siegen und zählt am meisten.|토요일은 13승 중 4승이 걸린 가장 중요한 날입니다.|周六占 13 胜中的 4 胜，最为关键。
pi_one_day|{share} of the week's points came on {day}. Spreading effort over more days protects the quota if one day goes badly.|{share} des points de la semaine ont été marqués le {day}. Répartir l'effort protège l'objectif si un jour se passe mal.|{share} недельных очков набрано в {day}. Распределение усилий по дням страхует норму, если один день не удастся.|Haftalık puanların {share} kadarı {day} günü geldi. Çabayı günlere yaymak, kötü geçen bir günde hedefi korur.|{share} punktów tygodnia zdobyto w {day}. Rozłożenie wysiłku chroni cel, gdy jeden dzień pójdzie źle.|El {share} de los puntos llegó el {day}. Repartir el esfuerzo protege el objetivo si un día sale mal.|{share} dos pontos veio em {day}. Distribuir o esforço protege a meta se um dia correr mal.|{share} der Wochenpunkte kamen am {day}. Verteilter Einsatz schützt das Soll, falls ein Tag schlecht läuft.|주간 포인트의 {share}가 {day}에 나왔습니다. 여러 날에 나눠 기여하면 하루를 망쳐도 목표를 지킬 수 있습니다.|本周 {share} 的积分来自 {day}。把努力分散到多天，即使某天不顺也能保住配额。
pi_up|Up {pct} vs {date} ({from} → {to}); alliance rank #{r1} → #{r2}.|En hausse de {pct} vs {date} ({from} → {to}) ; rang #{r1} → #{r2}.|Рост на {pct} к {date} ({from} → {to}); место #{r1} → #{r2}.|{date} tarihine göre {pct} artış ({from} → {to}); sıra #{r1} → #{r2}.|Wzrost o {pct} vs {date} ({from} → {to}); miejsce #{r1} → #{r2}.|Sube {pct} vs {date} ({from} → {to}); puesto #{r1} → #{r2}.|Subida de {pct} vs {date} ({from} → {to}); posição #{r1} → #{r2}.|Plus {pct} ggü. {date} ({from} → {to}); Rang #{r1} → #{r2}.|{date} 대비 {pct} 상승({from} → {to}), 연맹 순위 #{r1} → #{r2}.|较 {date} 上升 {pct}（{from} → {to}）；联盟排名 #{r1} → #{r2}。
pi_down|Down {pct} vs {date} ({from} → {to}); alliance rank #{r1} → #{r2}.|En baisse de {pct} vs {date} ({from} → {to}) ; rang #{r1} → #{r2}.|Спад на {pct} к {date} ({from} → {to}); место #{r1} → #{r2}.|{date} tarihine göre {pct} düşüş ({from} → {to}); sıra #{r1} → #{r2}.|Spadek o {pct} vs {date} ({from} → {to}); miejsce #{r1} → #{r2}.|Baja {pct} vs {date} ({from} → {to}); puesto #{r1} → #{r2}.|Descida de {pct} vs {date} ({from} → {to}); posição #{r1} → #{r2}.|Minus {pct} ggü. {date} ({from} → {to}); Rang #{r1} → #{r2}.|{date} 대비 {pct} 하락({from} → {to}), 연맹 순위 #{r1} → #{r2}.|较 {date} 下降 {pct}（{from} → {to}）；联盟排名 #{r1} → #{r2}。
pi_record|Reached the quota in {met} of {weeks} tracked weeks.|Objectif atteint {met} semaines sur {weeks} suivies.|Норма выполнена в {met} из {weeks} записанных недель.|Takip edilen {weeks} haftanın {met} haftasında hedefe ulaştı.|Cel osiągnięty w {met} z {weeks} zapisanych tygodni.|Alcanzó el objetivo en {met} de {weeks} semanas registradas.|Atingiu a meta em {met} de {weeks} semanas registadas.|Soll in {met} von {weeks} erfassten Wochen erreicht.|기록된 {weeks}주 중 {met}주 목표 달성.|在 {weeks} 个记录周中有 {met} 周达标。
pi_streak|Current streak: {n} weeks in a row.|Série en cours : {n} semaines d'affilée.|Текущая серия: {n} недель подряд.|Mevcut seri: üst üste {n} hafta.|Obecna seria: {n} tygodni z rzędu.|Racha actual: {n} semanas seguidas.|Sequência atual: {n} semanas seguidas.|Aktuelle Serie: {n} Wochen in Folge.|현재 {n}주 연속 달성 중.|当前连续 {n} 周达标。
pi_top|In the top {pct} of the alliance this week.|Dans les {pct} meilleurs de l'alliance cette semaine.|В лучших {pct} альянса на этой неделе.|Bu hafta ittifakın ilk {pct} diliminde.|W najlepszych {pct} sojuszu w tym tygodniu.|Entre el {pct} mejor de la alianza esta semana.|Entre os {pct} melhores da aliança esta semana.|Diese Woche unter den besten {pct} der Allianz.|이번 주 연맹 상위 {pct}.|本周位列联盟前 {pct}。
insights|Insights|Analyse|Выводы|İçgörüler|Wnioski|Claves|Destaques|Erkenntnisse|인사이트|洞察
daily_performance|Daily performance|Performance quotidienne|Результаты по дням|Günlük performans|Wyniki dzienne|Rendimiento diario|Desempenho diário|Tagesleistung|일별 성과|每日表现
alliance_median|Alliance median|Médiane de l'alliance|Медиана альянса|İttifak medyanı|Mediana sojuszu|Mediana de la alianza|Mediana da aliança|Allianz-Median|연맹 중앙값|联盟中位数
streak_weeks|{n}-week streak|Série de {n} semaines|Серия: {n} нед.|{n} haftalık seri|Seria {n} tyg.|Racha de {n} semanas|Sequência de {n} semanas|{n} Wochen in Serie|{n}주 연속|连续 {n} 周
"""


def translations():
    result = {lang: dict(values) for lang, values in T.items()}
    for line in TRANSLATIONS.strip().splitlines():
        key, *values = line.split('|')
        if len(values) != len(LOCALES):
            raise ValueError(f'{key}: expected {len(LOCALES)} translations, got {len(values)}')
        for lang, value in zip(LOCALES, values):
            if key in result[lang]:
                raise ValueError(f'Duplicate key: {lang}.{key}')
            result[lang][key] = value
    keys = set(result['en'])
    for lang, values in result.items():
        if set(values) != keys:
            raise ValueError(f'{lang}: translation keys differ')
        for key, value in values.items():
            if not value.strip():
                raise ValueError(f'{lang}.{key}: empty translation')
            if sorted(re.findall(r'\{(\w+)\}', value)) != sorted(re.findall(r'\{(\w+)\}', result['en'][key])):
                raise ValueError(f'{lang}.{key}: placeholders differ')
    return result


def build():
    result = translations()
    i18n_path = ROOT / 'data' / 'i18n.js'
    i18n_path.write_text(
        '// Generated by pipeline/build_i18n.py; edit the generator.\n'
        + 'window.I18N = ' + json.dumps(result, ensure_ascii=False, indent=2) + ';\n'
        + 'window.LANG_LOCALES = ' + json.dumps(LOCALES, ensure_ascii=False) + ';\n'
        + 'window.LANG_NAMES = ' + json.dumps(NAMES, ensure_ascii=False) + ';\n',
        encoding='utf-8',
    )
    stages = json.loads((ROOT / 'data' / 'competition_stages.json').read_text(encoding='utf-8'))
    stages_path = ROOT / 'data' / 'stages.js'
    stages_content = (
        '// Generated by pipeline/build_i18n.py from competition_stages.json.\n'
        + 'window.VS_STAGES = ' + json.dumps(stages, ensure_ascii=False, indent=2) + ';\n'
    )
    if not stages_path.exists() or stages_path.read_text(encoding='utf-8') != stages_content:
        stages_path.write_text(stages_content, encoding='utf-8')
    print(f'Generated {len(result)} languages × {len(result["en"])} keys and {len(stages["stages"])} stages')
    # Match the sister site: refresh asset hashes whenever translations are rebuilt.
    # build_week.py also invokes this stamper after rebuilding manifest data.
    stamper = ROOT / 'pipeline' / 'stamp_assets.py'
    if stamper.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('vs_stamp_assets', stamper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.stamp()


if __name__ == '__main__':
    build()
