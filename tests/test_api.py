"""Mock HTTP behavior; no network calls in unit tests."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from loader import load
api=load('api')
NOW=datetime(2026,11,26,10,tzinfo=timezone.utc)

class ApiTests(unittest.IsolatedAsyncioTestCase):
    def client(self,status=200,payload=None):
        response=MagicMock()
        response.status=status
        response.json=AsyncMock(return_value=payload)
        context=MagicMock()
        context.__aenter__=AsyncMock(return_value=response)
        context.__aexit__=AsyncMock(return_value=False)
        session=MagicMock()
        session.get.return_value=context
        return api.BkwApi(session),session,response
    async def test_exact_url_no_params_and_timeout(self):
        payload={'publication_timestamp':NOW.isoformat(),'prices':[{
            'start_timestamp':NOW.isoformat(),'end_timestamp':(NOW+timedelta(minutes=15)).isoformat(),
            'feed_in':[{'unit':'CHF_kWh','value':0.05}]}]}
        client,session,response=self.client(payload=payload)
        result=await client.async_fetch()
        self.assertEqual(result.slots[0].price,0.05)
        self.assertEqual(session.get.call_count,1)
        args,kwargs=session.get.call_args
        self.assertEqual(args[0],api.API_URL)
        self.assertNotIn('params',kwargs)
        self.assertEqual(kwargs['timeout'].total,30)
        self.assertFalse(kwargs['allow_redirects'])
    async def test_http_errors(self):
        for status in (302,400,404,429,500):
            client,_,response=self.client(status=status)
            with self.assertRaises(api.BkwApiError): await client.async_fetch()
            response.json.assert_not_called()
    async def test_invalid_json(self):
        client,_,response=self.client()
        response.json.side_effect=json.JSONDecodeError('bad','',0)
        with self.assertRaises(api.BkwApiError): await client.async_fetch()
    async def test_no_prices(self):
        client,_,_=self.client(payload={'publication_timestamp':NOW.isoformat(),'prices':[]})
        with self.assertRaises(api.BkwApiError): await client.async_fetch()
    async def test_timeout(self):
        client,session,_=self.client()
        session.get.side_effect=TimeoutError('timeout')
        with self.assertRaises(api.BkwApiError): await client.async_fetch()
    async def test_connection_error(self):
        client,session,_=self.client()
        session.get.side_effect=aiohttp.ClientConnectionError('offline')
        with self.assertRaises(api.BkwApiError): await client.async_fetch()
