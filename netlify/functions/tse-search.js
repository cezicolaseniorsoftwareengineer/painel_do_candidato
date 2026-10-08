const TSE_API = 'https://dadosabertos.tse.jus.br/api/3/action/package_search';

exports.handler = async (event) => {
  const query = String(event.queryStringParameters?.q || '').trim().slice(0, 120);
  if (!query) return json(400, { error: 'Query parameter q is required.' });
  const url = `${TSE_API}?q=${encodeURIComponent(query)}&rows=20`;
  try {
    const response = await fetch(url, { headers: { accept: 'application/json' } });
    if (!response.ok) return json(502, { error: 'TSE catalog unavailable.', upstreamStatus: response.status });
    const payload = await response.json();
    const results = payload?.result?.results || [];
    return json(200, { source: 'TSE Open Data CKAN', count: results.length, results });
  } catch (error) {
    return json(502, { error: 'TSE catalog request failed.' });
  }
};

function json(statusCode, body) {
  return { statusCode, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public, max-age=300' }, body: JSON.stringify(body) };
}
