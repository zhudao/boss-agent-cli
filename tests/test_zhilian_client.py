"""ZhilianClient P0 契约测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from boss_agent_cli.api.zhilian_client import (
	DETAIL_URL_TEMPLATE,
	RECOMMEND_URL,
	SEARCH_URL,
	USER_INFO_URL,
	ZhilianClient,
)


class _StubAuth:
	def __init__(self) -> None:
		self.token = {
			"cookies": {"zp_token": "token"},
			"user_agent": "UA",
			"x_zp_client_id": "client-id-1",
		}

	def get_token(self):
		return self.token

	def force_refresh(self, cdp_url=None):
		self.token = {**self.token, "zp_token": "refreshed"}


class TestZhilianClientStructure:
	"""ZhilianClient 类结构对齐 BossClient 的公开面。"""

	def test_can_instantiate_with_auth_manager(self) -> None:
		client = ZhilianClient(_StubAuth())
		assert client is not None

	def test_init_accepts_delay_keyword(self) -> None:
		client = ZhilianClient(_StubAuth(), delay=(2.0, 4.0))
		assert client._delay == (2.0, 4.0)

	def test_init_accepts_cdp_url_keyword(self) -> None:
		client = ZhilianClient(_StubAuth(), cdp_url="http://localhost:9222")
		assert client._cdp_url == "http://localhost:9222"

	def test_close_is_callable_and_idempotent(self) -> None:
		client = ZhilianClient(_StubAuth())
		client.close()
		client.close()  # 重复调用不抛错

	def test_get_client_applies_auth_headers(self) -> None:
		client = ZhilianClient(_StubAuth())
		httpx_client = client._get_client()
		assert httpx_client.headers["User-Agent"] == "UA"
		assert httpx_client.headers["x-zp-client-id"] == "client-id-1"
		assert httpx_client.cookies.get("zp_token") == "token"


class TestZhilianClientContextManager:
	"""with 上下文管理器支持。"""

	def test_enter_returns_self(self) -> None:
		client = ZhilianClient(_StubAuth())
		with client as c:
			assert c is client

	def test_exit_calls_close(self) -> None:
		client = ZhilianClient(_StubAuth())
		with client:
			assert not client._closed
		assert client._closed


class TestZhilianClientReadonlyMethods:
	"""P0 只读能力参数构造正确。"""

	def setup_method(self) -> None:
		self.client = ZhilianClient(_StubAuth())
		self.client._request = MagicMock(return_value={"code": 200, "data": {}})

	def test_search_jobs_minimal_params(self) -> None:
		self.client.search_jobs("Python")
		call = self.client._request.call_args
		assert call.args == ("GET", SEARCH_URL)
		assert call.kwargs["params"] == {"keyword": "Python", "pageNum": 1}

	def test_search_jobs_maps_supported_filters(self) -> None:
		self.client.search_jobs(
			"Python",
			page=2,
			page_size=20,
			city="530",
			salary="20K-30K",
			experience="3-5年",
			education="本科",
			scale="100-499人",
			industry="互联网",
			stage="A轮",
			job_type="全职",
		)
		params = self.client._request.call_args.kwargs["params"]
		assert params["keyword"] == "Python"
		assert params["pageNum"] == 2
		assert params["pageSize"] == 20
		assert params["cityId"] == "530"
		assert params["salary"] == "20K-30K"
		assert params["workExp"] == "3-5年"
		assert params["education"] == "本科"
		assert params["companySize"] == "100-499人"
		assert params["industry"] == "互联网"
		assert params["financingStage"] == "A轮"
		assert params["jobType"] == "全职"

	def test_job_detail_uses_path_param_url(self) -> None:
		self.client.job_detail("job-1")
		call = self.client._request.call_args
		assert call.args == ("GET", DETAIL_URL_TEMPLATE.format(job_id="job-1"))

	def test_recommend_jobs_uses_page_num(self) -> None:
		self.client.recommend_jobs(page=3)
		call = self.client._request.call_args
		assert call.args == ("GET", RECOMMEND_URL)
		assert call.kwargs["params"] == {"pageNum": 3}

	def test_user_info_no_params(self) -> None:
		self.client.user_info()
		call = self.client._request.call_args
		assert call.args == ("GET", USER_INFO_URL)


class TestPlatformInstanceRoutesToClient:
	"""get_platform_instance 按 platform 分发到正确的 client 类。"""

	def test_zhipin_platform_gets_boss_client(self) -> None:
		from unittest.mock import patch
		from boss_agent_cli.commands._platform import get_platform_instance
		from boss_agent_cli.platforms import BossPlatform

		ctx = MagicMock()
		ctx.obj = {"platform": "zhipin", "delay": (1.0, 2.0), "cdp_url": None}
		auth = MagicMock()

		with patch("boss_agent_cli.commands._platform.BossClient") as mock_boss_cls:
			plat = get_platform_instance(ctx, auth)
			assert isinstance(plat, BossPlatform)
			mock_boss_cls.assert_called_once()

	def test_zhilian_platform_gets_zhilian_client(self) -> None:
		from unittest.mock import patch
		from boss_agent_cli.commands._platform import get_platform_instance
		from boss_agent_cli.platforms import ZhilianPlatform

		ctx = MagicMock()
		ctx.obj = {"platform": "zhilian", "delay": (1.0, 2.0), "cdp_url": None}
		auth = MagicMock()

		with patch("boss_agent_cli.commands._platform.ZhilianClient") as mock_zhilian_cls:
			plat = get_platform_instance(ctx, auth)
			assert isinstance(plat, ZhilianPlatform)
			mock_zhilian_cls.assert_called_once()
