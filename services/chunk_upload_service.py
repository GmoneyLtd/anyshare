import hashlib
import os
import shutil
import uuid
from datetime import UTC, datetime, timedelta

from services.database_service import (
    add_file as db_add_file,
)
from services.database_service import (
    add_upload_chunk,
    create_upload_session,
    delete_upload_session,
    get_upload_session,
    get_uploaded_chunks,
    update_upload_session,
)
from services.logger_service import get_logger

app_logger = get_logger()

# 默认分片大小: 2MB
DEFAULT_CHUNK_SIZE = 2 * 1024 * 1024


def create_chunk_upload_session(file_name, file_size, user_info, client_ip, chunk_size=None):
    """
    创建分片上传会话

    Args:
        file_name: 文件名
        file_size: 文件大小
        user_info: 用户信息
        client_ip: 客户端IP
        chunk_size: 分片大小(可选)

    Returns:
        dict: 包含会话信息的字典
    """
    username = user_info.get("username", "anonymous")

    if chunk_size is None:
        chunk_size = DEFAULT_CHUNK_SIZE

    # 计算总分片数
    total_chunks = (file_size + chunk_size - 1) // chunk_size

    # 生成会话ID
    session_id = str(uuid.uuid4())

    # 创建临时目录
    temp_dir = f"./upload/temp/{session_id}"
    os.makedirs(temp_dir, exist_ok=True)

    # 创建数据库会话记录
    if create_upload_session(session_id, file_name, file_size, chunk_size, total_chunks, username, client_ip):
        app_logger.info(
            f"Created chunk upload session: {session_id}, file: {file_name}, size: {file_size}, chunks: {total_chunks}, user: {username}, Client-IP: {client_ip}"
        )

        return {
            "status": "success",
            "session_id": session_id,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "uploaded_chunks": [],
        }
    else:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        app_logger.error(
            f"Failed to create chunk upload session for file: {file_name}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Failed to create upload session"}


def upload_chunk(session_id, chunk_index, chunk_data, user_info, client_ip):
    """
    上传文件分片

    Args:
        session_id: 会话ID
        chunk_index: 分片索引
        chunk_data: 分片数据
        user_info: 用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含上传状态的字典
    """
    username = user_info.get("username", "anonymous")

    # 获取会话信息
    session = get_upload_session(session_id)
    if not session:
        app_logger.warning(
            f"Upload chunk failed: session not found {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Session not found"}

    # 验证用户权限
    if session["username"] != username:
        app_logger.warning(
            f"Upload chunk failed: permission denied for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Permission denied"}

    # 验证分片索引
    if chunk_index < 0 or chunk_index >= session["total_chunks"]:
        app_logger.warning(
            f"Upload chunk failed: invalid chunk index {chunk_index} for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Invalid chunk index"}

    try:
        # 计算分片哈希
        chunk_hash = hashlib.md5(chunk_data).hexdigest()

        # 保存分片到临时文件
        temp_dir = f"./upload/temp/{session_id}"
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")

        with open(chunk_path, "wb") as f:
            f.write(chunk_data)

        # 记录分片信息到数据库
        if add_upload_chunk(session_id, chunk_index, chunk_hash, len(chunk_data)):
            # 获取已上传分片列表
            uploaded_chunks = get_uploaded_chunks(session_id)
            uploaded_chunks_str = ",".join(map(str, uploaded_chunks))

            # 更新会话状态
            update_upload_session(session_id, uploaded_chunks=uploaded_chunks_str)

            app_logger.debug(
                f"Chunk uploaded successfully: session {session_id}, chunk {chunk_index}, size: {len(chunk_data)}, user: {username}, Client-IP: {client_ip}"
            )

            return {
                "status": "success",
                "chunk_index": chunk_index,
                "uploaded_chunks": uploaded_chunks,
                "total_chunks": session["total_chunks"],
            }
        else:
            # 删除临时文件
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

            app_logger.error(
                f"Failed to record chunk: session {session_id}, chunk {chunk_index}, user: {username}, Client-IP: {client_ip}"
            )
            return {"status": "error", "message": "Failed to record chunk"}

    except Exception as e:
        app_logger.error(
            f"Upload chunk error: session {session_id}, chunk {chunk_index}, error: {str(e)}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": f"Upload chunk failed: {str(e)}"}


def complete_chunk_upload(session_id, user_info, client_ip, upload_folder, expiry_option=None, password=None):
    """
    完成分片上传, 合并文件

    Args:
        session_id: 会话ID
        user_info: 用户信息
        client_ip: 客户端IP
        upload_folder: 上传文件夹路径
        expiry_option: 过期时间选项
        password: 文件密码(可选)

    Returns:
        dict: 包含完成状态和文件信息的字典
    """
    username = user_info.get("username", "anonymous")

    # 获取会话信息
    session = get_upload_session(session_id)
    if not session:
        app_logger.warning(
            f"Complete upload failed: session not found {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Session not found"}

    # 验证用户权限
    if session["username"] != username:
        app_logger.warning(
            f"Complete upload failed: permission denied for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Permission denied"}

    # 检查所有分片是否已上传
    uploaded_chunks = get_uploaded_chunks(session_id)
    expected_chunks = list(range(session["total_chunks"]))

    if set(uploaded_chunks) != set(expected_chunks):
        missing_chunks = set(expected_chunks) - set(uploaded_chunks)
        app_logger.warning(
            f"Complete upload failed: missing chunks {missing_chunks} for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": f"Missing chunks: {list(missing_chunks)}"}

    try:
        # 生成最终文件哈希
        hash_input = f"{session['file_name']}_{datetime.now(UTC).timestamp()}"
        file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        final_path = os.path.join(upload_folder, file_hash)

        # 合并分片
        temp_dir = f"./upload/temp/{session_id}"
        with open(final_path, "wb") as final_file:
            for chunk_index in range(session["total_chunks"]):
                chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as chunk_file:
                        final_file.write(chunk_file.read())
                else:
                    # 清理已创建的文件
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    app_logger.error(
                        f"Complete upload failed: chunk file missing {chunk_path}, session {session_id}, user: {username}, Client-IP: {client_ip}"
                    )
                    return {"status": "error", "message": f"Chunk file missing: {chunk_index}"}

        # 验证文件大小
        actual_size = os.path.getsize(final_path)
        if actual_size != session["file_size"]:
            os.remove(final_path)
            app_logger.error(
                f"Complete upload failed: file size mismatch, expected: {session['file_size']}, actual: {actual_size}, session {session_id}, user: {username}, Client-IP: {client_ip}"
            )
            return {"status": "error", "message": "File size mismatch"}

        # 根据过期选项计算过期时间
        expiry_map = {
            "1 hour": datetime.now(UTC) + timedelta(hours=1),
            "1 day": datetime.now(UTC) + timedelta(days=1),
            "1 week": datetime.now(UTC) + timedelta(weeks=1),
            "1 month": datetime.now(UTC) + timedelta(days=30),
            "forever": datetime.now(UTC) + timedelta(days=365 * 10),
        }
        expiry_date = expiry_map.get(expiry_option, datetime.now(UTC) + timedelta(days=1))

        # 保存到数据库
        password = db_add_file(
            session["file_name"], file_hash, session["file_size"], expiry_date, client_ip, username, password
        )

        # 更新会话状态
        update_upload_session(session_id, file_hash=file_hash, status="completed")

        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # 清理会话记录(可选, 也可以保留用于审计)
        # delete_upload_session(session_id)

        app_logger.info(
            f"Chunk upload completed successfully: session {session_id}, file: {session['file_name']}, hash: {file_hash}, size: {session['file_size']}, expiry: {expiry_option}, user: {username}, Client-IP: {client_ip}"
        )

        return {
            "status": "success",
            "file_hash": file_hash,
            "file_name": session["file_name"],
            "file_size": session["file_size"],
            "password": password,
        }

    except Exception as e:
        # 清理文件
        if "final_path" in locals() and os.path.exists(final_path):
            os.remove(final_path)

        app_logger.error(
            f"Complete upload error: session {session_id}, error: {str(e)}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": f"Complete upload failed: {str(e)}"}


def get_chunk_upload_status(session_id, user_info, client_ip):
    """
    获取分片上传状态

    Args:
        session_id: 会话ID
        user_info: 用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含上传状态的字典
    """
    username = user_info.get("username", "anonymous")

    # 获取会话信息
    session = get_upload_session(session_id)
    if not session:
        app_logger.warning(
            f"Get upload status failed: session not found {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Session not found"}

    # 验证用户权限
    if session["username"] != username:
        app_logger.warning(
            f"Get upload status failed: permission denied for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Permission denied"}

    # 获取已上传分片列表
    uploaded_chunks = get_uploaded_chunks(session_id)

    return {
        "status": "success",
        "session_id": session_id,
        "file_name": session["file_name"],
        "file_size": session["file_size"],
        "chunk_size": session["chunk_size"],
        "total_chunks": session["total_chunks"],
        "uploaded_chunks": uploaded_chunks,
        "upload_status": session["status"],
        "progress": len(uploaded_chunks) / session["total_chunks"] * 100,
    }


def cancel_chunk_upload(session_id, user_info, client_ip):
    """
    取消分片上传

    Args:
        session_id: 会话ID
        user_info: 用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含取消状态的字典
    """
    username = user_info.get("username", "anonymous")

    # 获取会话信息
    session = get_upload_session(session_id)
    if not session:
        app_logger.warning(
            f"Cancel upload failed: session not found {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Session not found"}

    # 验证用户权限
    if session["username"] != username:
        app_logger.warning(
            f"Cancel upload failed: permission denied for session {session_id}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Permission denied"}

    try:
        # 清理临时文件
        temp_dir = f"./upload/temp/{session_id}"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # 删除会话记录
        delete_upload_session(session_id)

        app_logger.info(f"Upload session cancelled: {session_id}, user: {username}, Client-IP: {client_ip}")

        return {"status": "success", "message": "Upload cancelled"}

    except Exception as e:
        app_logger.error(
            f"Cancel upload error: session {session_id}, error: {str(e)}, user: {username}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": f"Cancel upload failed: {str(e)}"}
