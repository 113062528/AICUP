
import warnings
from typing import Any, List, Optional, Union, Dict
from tenacity import (
    Retrying,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

import voyageai
from voyageai._base import _BaseClient  
import voyageai.error as error
from voyageai.object import RerankingObject

class Client(_BaseClient):
    """Voyage AI Client

    Args:
        api_key (str): Your API key.
        max_retries (int): Maximum number of retries if API call fails.
        timeout (float): Timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 0,
        timeout: Optional[float] = None,
    ) ->None:
        super().__init__(api_key, max_retries, timeout)

        self.retry_controller = Retrying(
            reraise=True,
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential_jitter(initial=1, max=16),
            retry=(
                retry_if_exception_type(error.RateLimitError)
                | retry_if_exception_type(error.ServiceUnavailableError)
                | retry_if_exception_type(error.Timeout)
            ),
        )

    def rerank(
        self,
        query: str,
        documents: List[str],
        model: str,
        top_k: Optional[int] = None,
        truncation: bool = True,
    ) -> RerankingObject:

        for attempt in self.retry_controller:
            with attempt:
                response = voyageai.Reranking.create(
                    query=query,
                    documents=documents,
                    model=model,
                    top_k=top_k,
                    truncation=truncation,
                    **self._params,
                )

        result = RerankingObject(documents, response)
        return result


def retrieve(client,qs, source, corpus_dict):
    """
    根據查詢從語料庫中檢索最相關的文件。

    Args:
        client (Client): 用於重新排序文件的Voyage AI客戶端。
        qs (str): 查詢字串。
        source (List[int]): 要考慮的來源文件ID列表。
        corpus_dict (Dict[int, str]): 一個字典，其中鍵是文件ID，值是文件文本。

    Returns:
        int: 最相關文件的文件ID。
    """
    filtered_corpus = [corpus_dict[int(file)] for file in source]

    reranking = client.rerank(qs, filtered_corpus, model="rerank-2", top_k=1)#呼叫外部API

    ans = reranking.results[0].document

    # 找回與最佳匹配文本相對應的檔案名
    res = [key for key, value in corpus_dict.items() if value == ans]

    return res[0]  # 回傳檔案名
