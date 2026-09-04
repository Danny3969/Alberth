#!/usr/bin/env bash
# Script de limpieza de cron jobs duplicados de Alberth
# Elimina todos los jobs de higiene de memoria duplicados
# y conserva SOLO uno llamado "daily-memory-hygiene"

echo "🧹 Iniciando limpieza de cron jobs duplicados..."

IDS=(
  03c0f8a3-16eb-44bc-a0ee-ef5d89aa5382
  07f7fe96-4cf8-45bb-a61e-e6651bcfdd5e
  144ede59-b958-4af7-8fe2-2a5f090f7a03
  15531573-a0f3-46e5-9905-1cb49439c570
  175933c1-39a4-4cf5-9a16-d34250242300
  27dfa890-bbae-4ad6-a5a5-8292d7c080ed
  2c6789e5-0258-489e-b2f9-e8198efd8014
  35587c9e-38c0-4640-bcbb-e72c448fe86a
  38be1a8b-60c7-455f-9f0f-e22c219c3894
  3b23d670-f6fc-46b2-b6da-0e51a80a7dc9
  3b795e1b-9981-4b48-b3b6-eff8ceb7393c
  410d6034-b4cc-4a76-9ce7-598fcd44368a
  43439fa7-9018-410c-a8bf-faa23b3aa64d
  43aacb23-0ecb-4fc1-b36a-0cc740a3104a
  44e9a5fd-0fd9-411e-a06e-e5044df3f3c6
  48426659-e812-4c8e-892e-d6898988139f
  4df3803e-92da-4a33-a171-ed621f56d39d
  4f6e7373-3301-494c-a0b2-4e02fa29a81f
  50d3674b-39cc-49b8-b59d-f8b8d0a3daa8
  50ff941b-8e2c-4204-8e22-1833c3ce6c0b
  5967c2ff-4588-459a-9fdb-7f9df91088e9
  603bb7be-a212-4cbc-8108-aaca5cde23ff
  6377ca66-3cc1-487b-a5d1-37d0ce87246a
  6bf5d42e-52b0-4ec9-b62e-31c3f13afd29
  6e6de3a8-3fe9-4484-9f05-00bd6ea60ff8
  702f38f0-96a0-452c-95d3-454088857682
  7a61e0dd-721c-4238-afe6-cf8fd1ab101c
  7a842ae5-0f53-45b7-ba0b-0f01858c7119
  7acc53e3-405a-4562-b87d-37b6d9f39b18
  7c1ef74f-a804-4b5f-83a8-21d1addae61e
  81237a8b-0920-4b2d-a909-0a221bc9ad72
  86f0abc0-6360-4237-9911-8b931798dfb5
  9658f4c4-9fcd-440f-be92-08e4df1c3ddf
  97593cdb-54f7-4c30-80ad-a7491eb71d9f
  995be2bc-9361-478a-bb67-2701c5532064
  9d004e14-f93d-433c-b984-4ab5812059cf
  9f7d5af8-9314-41ae-a127-f199a6ba671c
  a0776c0d-512d-4cb3-ba3a-b9b5b75295d9
  a58f935f-481a-49e9-9afb-89c196d4e921
  a8f759a4-759d-47d2-812e-ee0440b8b4ce
  aa633e12-747b-4200-80ea-f21162b297d6
  acbdc47b-273e-4a19-a714-df56fbb221f6
  af8f7650-2199-4596-8100-47b0f6a13564
  b179ea80-8118-44aa-a731-af9e22ba1505
  b36c4143-f3e5-4c01-898e-52d70143ecdd
  b724736c-d519-46b9-ab98-2c3f1580c638
  c39f7c31-5ceb-4762-9de9-c0758efd40ad
  dbbb0d90-c758-467a-9c1c-00ea01f90866
  dcd70491-c84f-4dbf-82bf-677dc29d7615
  e61427b2-4c78-47b2-ab40-eb32735b6f24
  ebba407b-4c07-4a27-8e45-c665dc8a5a1f
  ec870947-02a6-47b0-a49f-559c39a03eaf
  f2091a1a-67a7-40c9-9eda-46d8e9f54310
  f49968ec-0bdf-4521-b6ae-6f9f9644dbab
  faba9af0-7230-47e6-ac04-92cdf86d66ac
  fcdd5bcc-d9b9-4397-9c82-cb81129dfc50
)

TOTAL=${#IDS[@]}
REMOVED=0
FAILED=0

for id in "${IDS[@]}"; do
  echo -n "  Eliminando $id... "
  if openclaw cron rm "$id" 2>/dev/null; then
    echo "✅"
    ((REMOVED++))
  else
    echo "❌ (falló)"
    ((FAILED++))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Eliminados: $REMOVED / $TOTAL"
echo "❌ Fallados:   $FAILED / $TOTAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Verificando cron jobs restantes..."
openclaw cron list 2>/dev/null | grep -E "persistent.memory|nightly-memory" | wc -l
echo "job(s) de higiene de memoria restantes (debería ser 0)"
